use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use hmac::{Hmac, Mac};
use keyring::{Entry, Error as KeyringError};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::Manager;

const TRIAL_DURATION_SECONDS: i64 = 7 * 24 * 60 * 60;
const TRIAL_SCHEMA_VERSION: i64 = 1;
const SERVICE: &str = "com.voidstation.melody.trial";
const ACCOUNT: &str = "trial-state-v1";

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
struct TrialState {
    schema_version: i64,
    install_id: String,
    first_run_at: i64,
    last_seen_at: i64,
    expires_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SecureTrialPayload {
    state: TrialState,
    integrity_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MirrorEnvelope {
    payload: TrialState,
    mac: String,
}

#[derive(Debug, Clone, Serialize)]
struct TrialRuntime {
    data_dir: String,
    integrity_key: String,
}

fn now_epoch() -> Result<i64, String> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs() as i64)
        .map_err(|error| format!("system clock is before Unix epoch: {error}"))
}

fn secure_entry() -> Result<Entry, String> {
    Entry::new(SERVICE, ACCOUNT).map_err(|error| format!("secure store unavailable: {error}"))
}

fn new_install_id() -> String {
    let mut bytes = [0_u8; 16];
    rand::thread_rng().fill_bytes(&mut bytes);
    let hex = bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    format!(
        "{}-{}-4{}-{}-{}",
        &hex[0..8],
        &hex[8..12],
        &hex[13..16],
        &hex[16..20],
        &hex[20..32]
    )
}

fn new_integrity_key() -> String {
    let mut bytes = [0_u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    URL_SAFE_NO_PAD.encode(bytes)
}

fn parse_key(value: &str) -> Result<Vec<u8>, String> {
    let key = URL_SAFE_NO_PAD
        .decode(value)
        .map_err(|error| format!("invalid trial integrity key: {error}"))?;
    if key.len() < 32 {
        return Err("trial integrity key is shorter than 256 bits".to_string());
    }
    Ok(key)
}

fn validate_state(state: &TrialState) -> Result<(), String> {
    if state.schema_version != TRIAL_SCHEMA_VERSION
        || state.install_id.is_empty()
        || state.first_run_at < 0
        || state.last_seen_at < state.first_run_at
        || state.expires_at != state.first_run_at + TRIAL_DURATION_SECONDS
    {
        return Err("trial state failed validation".to_string());
    }
    Ok(())
}

fn mac_for_state(state: &TrialState, key: &[u8]) -> Result<String, String> {
    let encoded = serde_json::to_vec(state)
        .map_err(|error| format!("trial serialization failed: {error}"))?;
    let mut mac =
        HmacSha256::new_from_slice(key).map_err(|error| format!("trial HMAC failed: {error}"))?;
    mac.update(&encoded);
    Ok(URL_SAFE_NO_PAD.encode(mac.finalize().into_bytes()))
}

fn mirror_path(data_dir: &Path) -> PathBuf {
    data_dir.join("trial-state-v1.json")
}

fn read_mirror(path: &Path, key: Option<&[u8]>) -> Result<Option<TrialState>, String> {
    let raw = match fs::read_to_string(path) {
        Ok(value) => value,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(format!("trial mirror read failed: {error}")),
    };
    let envelope: MirrorEnvelope = serde_json::from_str(&raw)
        .map_err(|error| format!("trial mirror is malformed: {error}"))?;
    validate_state(&envelope.payload)?;
    if let Some(key) = key {
        let expected = mac_for_state(&envelope.payload, key)?;
        if expected != envelope.mac {
            return Err("trial mirror integrity check failed".to_string());
        }
    }
    Ok(Some(envelope.payload))
}

fn write_mirror(path: &Path, state: &TrialState, key: &[u8]) -> Result<(), String> {
    validate_state(state)?;
    let envelope = MirrorEnvelope {
        payload: state.clone(),
        mac: mac_for_state(state, key)?,
    };
    let encoded = serde_json::to_vec(&envelope)
        .map_err(|error| format!("trial mirror serialization failed: {error}"))?;
    let parent = path
        .parent()
        .ok_or_else(|| "trial mirror has no parent".to_string())?;
    fs::create_dir_all(parent).map_err(|error| format!("trial data directory failed: {error}"))?;
    let temporary = path.with_extension("json.tmp");
    fs::write(&temporary, encoded)
        .map_err(|error| format!("trial mirror temp write failed: {error}"))?;
    fs::rename(&temporary, path)
        .map_err(|error| format!("trial mirror replace failed: {error}"))?;
    Ok(())
}

fn read_secure(entry: &Entry) -> Result<Option<SecureTrialPayload>, String> {
    match entry.get_password() {
        Ok(value) => {
            let payload = serde_json::from_str::<SecureTrialPayload>(&value)
                .map_err(|error| format!("secure trial payload is malformed: {error}"))?;
            validate_state(&payload.state)?;
            parse_key(&payload.integrity_key)?;
            Ok(Some(payload))
        }
        Err(KeyringError::NoEntry) => Ok(None),
        Err(error) => Err(format!("secure trial read failed: {error}")),
    }
}

fn write_secure(entry: &Entry, state: &TrialState, integrity_key: &str) -> Result<(), String> {
    validate_state(state)?;
    parse_key(integrity_key)?;
    let payload = SecureTrialPayload {
        state: state.clone(),
        integrity_key: integrity_key.to_string(),
    };
    let encoded = serde_json::to_string(&payload)
        .map_err(|error| format!("secure trial serialization failed: {error}"))?;
    entry
        .set_password(&encoded)
        .map_err(|error| format!("secure trial write failed: {error}"))
}

fn merge_states(secure: &TrialState, mirror: &TrialState) -> TrialState {
    let first_run_at = secure.first_run_at.min(mirror.first_run_at);
    TrialState {
        schema_version: TRIAL_SCHEMA_VERSION,
        install_id: secure.install_id.clone(),
        first_run_at,
        last_seen_at: secure.last_seen_at.max(mirror.last_seen_at),
        expires_at: first_run_at + TRIAL_DURATION_SECONDS,
    }
}

fn bootstrap_trial(data_dir: &Path) -> Result<TrialRuntime, String> {
    let entry = secure_entry()?;
    let path = mirror_path(data_dir);
    let secure = read_secure(&entry)?;
    let (mut state, integrity_key) = match secure {
        Some(payload) => {
            let key = parse_key(&payload.integrity_key)?;
            let mirror = read_mirror(&path, Some(&key)).unwrap_or(None);
            let state = mirror
                .as_ref()
                .map(|value| merge_states(&payload.state, value))
                .unwrap_or(payload.state);
            (state, payload.integrity_key)
        }
        None => {
            let mirror = read_mirror(&path, None)?;
            let state = mirror.unwrap_or_else(|| {
                let first_run_at = now_epoch().unwrap_or(0);
                TrialState {
                    schema_version: TRIAL_SCHEMA_VERSION,
                    install_id: new_install_id(),
                    first_run_at,
                    last_seen_at: first_run_at,
                    expires_at: first_run_at + TRIAL_DURATION_SECONDS,
                }
            });
            (state, new_integrity_key())
        }
    };
    if let Ok(now) = now_epoch() {
        if now > state.last_seen_at {
            state.last_seen_at = now;
        }
    }
    let key = parse_key(&integrity_key)?;
    write_secure(&entry, &state, &integrity_key)?;
    write_mirror(&path, &state, &key)?;
    Ok(TrialRuntime {
        data_dir: data_dir.to_string_lossy().to_string(),
        integrity_key,
    })
}

#[tauri::command]
fn trial_runtime(app: tauri::AppHandle) -> Result<TrialRuntime, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("app data directory unavailable: {error}"))?;
    bootstrap_trial(&data_dir)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            #[cfg(any(
                all(target_os = "macos", target_arch = "aarch64"),
                all(windows, target_arch = "x86_64")
            ))]
            app.handle()
                .plugin(tauri_plugin_updater::Builder::new().build())?;

            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![trial_runtime])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mirror_hmac_changes_when_state_changes() {
        let state = TrialState {
            schema_version: TRIAL_SCHEMA_VERSION,
            install_id: "install-1".to_string(),
            first_run_at: 100,
            last_seen_at: 100,
            expires_at: 100 + TRIAL_DURATION_SECONDS,
        };
        let mut changed = state.clone();
        changed.last_seen_at += 1;
        let key = [7_u8; 32];
        assert_ne!(
            mac_for_state(&state, &key).unwrap(),
            mac_for_state(&changed, &key).unwrap()
        );
    }

    #[test]
    fn merge_uses_oldest_start_and_latest_seen() {
        let secure = TrialState {
            schema_version: TRIAL_SCHEMA_VERSION,
            install_id: "secure".to_string(),
            first_run_at: 100,
            last_seen_at: 500,
            expires_at: 100 + TRIAL_DURATION_SECONDS,
        };
        let mirror = TrialState {
            schema_version: TRIAL_SCHEMA_VERSION,
            install_id: "mirror".to_string(),
            first_run_at: 200,
            last_seen_at: 900,
            expires_at: 200 + TRIAL_DURATION_SECONDS,
        };
        let merged = merge_states(&secure, &mirror);
        assert_eq!(merged.install_id, "secure");
        assert_eq!(merged.first_run_at, 100);
        assert_eq!(merged.last_seen_at, 900);
        assert_eq!(merged.expires_at, 100 + TRIAL_DURATION_SECONDS);
    }
}
