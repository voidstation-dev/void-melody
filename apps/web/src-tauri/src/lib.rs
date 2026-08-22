use serde::Serialize;
use std::path::{Path, PathBuf};
use tauri::Manager;

#[derive(Clone, Copy)]
enum RuntimeTarget {
    MacosArm64,
    WindowsX64,
}

impl RuntimeTarget {
    fn current() -> Option<Self> {
        if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
            Some(Self::MacosArm64)
        } else if cfg!(all(target_os = "windows", target_arch = "x86_64")) {
            Some(Self::WindowsX64)
        } else {
            None
        }
    }

    fn platform(self) -> &'static str {
        match self {
            Self::MacosArm64 => "macos",
            Self::WindowsX64 => "windows",
        }
    }

    fn target_triple(self) -> &'static str {
        match self {
            Self::MacosArm64 => "aarch64-apple-darwin",
            Self::WindowsX64 => "x86_64-pc-windows-msvc",
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
enum RuntimeResourceLocation {
    ResourceDirectory,
    ExecutableDirectory,
}

#[derive(Debug, PartialEq, Eq)]
struct RuntimeResourceCheck {
    report_name: &'static str,
    location: RuntimeResourceLocation,
    runtime_name: &'static str,
}

fn runtime_resource_checks(target: RuntimeTarget) -> [RuntimeResourceCheck; 3] {
    match target {
        RuntimeTarget::MacosArm64 => [
            RuntimeResourceCheck {
                report_name: "bin/Voice.json",
                location: RuntimeResourceLocation::ResourceDirectory,
                runtime_name: "bin/Voice.json",
            },
            RuntimeResourceCheck {
                report_name: "bin/ffmpeg",
                location: RuntimeResourceLocation::ExecutableDirectory,
                runtime_name: "ffmpeg",
            },
            RuntimeResourceCheck {
                report_name: "bin/melody-api-aarch64-apple-darwin",
                location: RuntimeResourceLocation::ExecutableDirectory,
                runtime_name: "melody-api",
            },
        ],
        RuntimeTarget::WindowsX64 => [
            RuntimeResourceCheck {
                report_name: "bin/Voice.json",
                location: RuntimeResourceLocation::ResourceDirectory,
                runtime_name: "bin/Voice.json",
            },
            RuntimeResourceCheck {
                report_name: "bin/ffmpeg.exe",
                location: RuntimeResourceLocation::ExecutableDirectory,
                runtime_name: "ffmpeg.exe",
            },
            RuntimeResourceCheck {
                report_name: "bin/melody-api-x86_64-pc-windows-msvc.exe",
                location: RuntimeResourceLocation::ExecutableDirectory,
                runtime_name: "melody-api.exe",
            },
        ],
    }
}

fn runtime_resource_path(
    check: &RuntimeResourceCheck,
    resource_dir: &Path,
    executable_dir: &Path,
) -> PathBuf {
    match check.location {
        RuntimeResourceLocation::ResourceDirectory => resource_dir.join(check.runtime_name),
        RuntimeResourceLocation::ExecutableDirectory => executable_dir.join(check.runtime_name),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::{Path, PathBuf};

    #[test]
    fn macos_sidecars_are_checked_next_to_the_executable() {
        assert_eq!(
            runtime_resource_checks(RuntimeTarget::MacosArm64),
            [
                RuntimeResourceCheck {
                    report_name: "bin/Voice.json",
                    location: RuntimeResourceLocation::ResourceDirectory,
                    runtime_name: "bin/Voice.json",
                },
                RuntimeResourceCheck {
                    report_name: "bin/ffmpeg",
                    location: RuntimeResourceLocation::ExecutableDirectory,
                    runtime_name: "ffmpeg",
                },
                RuntimeResourceCheck {
                    report_name: "bin/melody-api-aarch64-apple-darwin",
                    location: RuntimeResourceLocation::ExecutableDirectory,
                    runtime_name: "melody-api",
                },
            ]
        );
    }

    #[test]
    fn sidecar_runtime_paths_resolve_from_the_current_executable_directory() {
        let checks = runtime_resource_checks(RuntimeTarget::MacosArm64);

        assert_eq!(
            runtime_resource_path(
                &checks[2],
                Path::new("/bundle/Resources"),
                Path::new("/bundle/MacOS"),
            ),
            PathBuf::from("/bundle/MacOS/melody-api")
        );
    }

    #[test]
    fn windows_sidecars_are_checked_next_to_the_executable() {
        assert_eq!(
            runtime_resource_checks(RuntimeTarget::WindowsX64),
            [
                RuntimeResourceCheck {
                    report_name: "bin/Voice.json",
                    location: RuntimeResourceLocation::ResourceDirectory,
                    runtime_name: "bin/Voice.json",
                },
                RuntimeResourceCheck {
                    report_name: "bin/ffmpeg.exe",
                    location: RuntimeResourceLocation::ExecutableDirectory,
                    runtime_name: "ffmpeg.exe",
                },
                RuntimeResourceCheck {
                    report_name: "bin/melody-api-x86_64-pc-windows-msvc.exe",
                    location: RuntimeResourceLocation::ExecutableDirectory,
                    runtime_name: "melody-api.exe",
                },
            ]
        );
    }
}

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

    let Some(target) = RuntimeTarget::current() else {
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
    let executable_dir = std::env::current_exe()
        .map_err(|_| "Unable to locate runtime executable".to_string())?
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| "Unable to locate runtime executable".to_string())?;
    let resources = runtime_resource_checks(target)
        .into_iter()
        .map(|check| RuntimeResourceStatus {
            name: check.report_name.to_string(),
            present: runtime_resource_path(&check, &resource_dir, &executable_dir).is_file(),
        })
        .collect();

    Ok(RuntimePreflight {
        platform: target.platform(),
        arch,
        target_triple: target.target_triple(),
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
