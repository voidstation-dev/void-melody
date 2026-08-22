use serde::Serialize;
use tauri::Manager;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeResourceStatus {
    name: String,
    present: bool,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimePreflight {
    platform: &'static str,
    arch: &'static str,
    target_triple: &'static str,
    resources: Vec<RuntimeResourceStatus>,
    host_environment_required: Vec<String>,
}

#[tauri::command]
fn get_runtime_preflight(app: tauri::AppHandle) -> Result<RuntimePreflight, String> {
    let arch = if cfg!(target_arch = "aarch64") {
        "aarch64"
    } else if cfg!(target_arch = "x86_64") {
        "x86_64"
    } else {
        "unknown"
    };

    let (platform, target_triple, resource_names) =
        if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
            (
                "macos",
                "aarch64-apple-darwin",
                vec![
                    "bin/Voice.json",
                    "bin/ffmpeg",
                    "bin/melody-api-aarch64-apple-darwin",
                ],
            )
        } else if cfg!(all(target_os = "windows", target_arch = "x86_64")) {
            (
                "windows",
                "x86_64-pc-windows-msvc",
                vec![
                    "bin/Voice.json",
                    "bin/ffmpeg.exe",
                    "bin/melody-api-x86_64-pc-windows-msvc.exe",
                ],
            )
        } else {
            return Ok(RuntimePreflight {
                platform: "unsupported",
                arch,
                target_triple: "unsupported",
                resources: Vec::new(),
                host_environment_required: Vec::new(),
            });
        };

    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|_| "Unable to locate runtime resources".to_string())?;
    let resources = resource_names
        .into_iter()
        .map(|name| RuntimeResourceStatus {
            name: name.to_string(),
            present: resource_dir.join(name).is_file(),
        })
        .collect();

    Ok(RuntimePreflight {
        platform,
        arch,
        target_triple,
        resources,
        host_environment_required: Vec::new(),
    })
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
        .invoke_handler(tauri::generate_handler![get_runtime_preflight])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
