use serde::Serialize;
use std::fs;
use std::num::NonZeroU32;
use std::path::{Path, PathBuf};
#[cfg(target_os = "macos")]
use std::time::{Duration, Instant};
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

fn validate_sidecar_pid(pid: u32) -> Result<NonZeroU32, ()> {
    let pid = NonZeroU32::new(pid).ok_or(())?;

    #[cfg(unix)]
    if pid.get() > i32::MAX as u32 {
        return Err(());
    }

    Ok(pid)
}

fn expected_sidecar_path() -> std::io::Result<PathBuf> {
    let executable_dir = std::env::current_exe()?
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| std::io::Error::other("Unable to locate runtime executable"))?;

    #[cfg(windows)]
    let filename = "melody-api.exe";
    #[cfg(not(windows))]
    let filename = "melody-api";

    Ok(executable_dir.join(filename))
}

fn paths_match(actual: &Path, expected: &Path) -> bool {
    let actual = fs::canonicalize(actual).unwrap_or_else(|_| actual.to_path_buf());
    let expected = fs::canonicalize(expected).unwrap_or_else(|_| expected.to_path_buf());

    #[cfg(windows)]
    {
        actual
            .to_string_lossy()
            .eq_ignore_ascii_case(&expected.to_string_lossy())
    }

    #[cfg(not(windows))]
    {
        actual == expected
    }
}

#[cfg(target_os = "macos")]
fn process_executable_path(pid: NonZeroU32) -> std::io::Result<Option<PathBuf>> {
    let mut buffer = [0_u8; 4096];
    let length = unsafe {
        libc::proc_pidpath(
            pid.get() as libc::pid_t,
            buffer.as_mut_ptr().cast(),
            buffer.len() as u32,
        )
    };
    if length <= 0 {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() == Some(libc::ESRCH) {
            return Ok(None);
        }
        return Err(error);
    }

    Ok(Some(PathBuf::from(
        String::from_utf8_lossy(&buffer[..length as usize]).into_owned(),
    )))
}

#[cfg(windows)]
fn process_executable_path(pid: NonZeroU32) -> std::io::Result<Option<PathBuf>> {
    use windows_sys::Win32::Foundation::{CloseHandle, ERROR_INVALID_PARAMETER};
    use windows_sys::Win32::System::Threading::{OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION};

    let process = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid.get()) };
    if process.is_null() {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() == Some(ERROR_INVALID_PARAMETER as i32) {
            return Ok(None);
        }
        return Err(error);
    }

    let path = process_executable_path_from_handle(process);
    unsafe { CloseHandle(process) };
    Ok(Some(path?))
}

#[cfg(windows)]
fn process_executable_path_from_handle(
    process: windows_sys::Win32::Foundation::HANDLE,
) -> std::io::Result<PathBuf> {
    use std::os::windows::ffi::OsStringExt;
    use windows_sys::Win32::System::Threading::QueryFullProcessImageNameW;

    let mut buffer = vec![0_u16; 32_768];
    let mut length = buffer.len() as u32;
    let result =
        unsafe { QueryFullProcessImageNameW(process, 0, buffer.as_mut_ptr(), &mut length) };
    if result == 0 {
        return Err(std::io::Error::last_os_error());
    }

    Ok(PathBuf::from(std::ffi::OsString::from_wide(
        &buffer[..length as usize],
    )))
}

#[cfg(target_os = "macos")]
fn process_start_time(pid: NonZeroU32) -> std::io::Result<Option<u128>> {
    let mut info = std::mem::MaybeUninit::<libc::proc_bsdinfo>::zeroed();
    let result = unsafe {
        libc::proc_pidinfo(
            pid.get() as libc::pid_t,
            libc::PROC_PIDTBSDINFO,
            0,
            info.as_mut_ptr().cast(),
            std::mem::size_of::<libc::proc_bsdinfo>() as i32,
        )
    };
    if result <= 0 {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() == Some(libc::ESRCH) {
            return Ok(None);
        }
        return Err(error);
    }

    let info = unsafe { info.assume_init() };
    Ok(Some(
        u128::from(info.pbi_start_tvsec) * 1_000_000 + u128::from(info.pbi_start_tvusec),
    ))
}

#[cfg(windows)]
fn process_start_time(pid: NonZeroU32) -> std::io::Result<Option<u128>> {
    use windows_sys::Win32::Foundation::{CloseHandle, ERROR_INVALID_PARAMETER, FILETIME};
    use windows_sys::Win32::System::Threading::{
        GetProcessTimes, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
    };

    let process = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid.get()) };
    if process.is_null() {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() == Some(ERROR_INVALID_PARAMETER as i32) {
            return Ok(None);
        }
        return Err(error);
    }

    let start_time = process_start_time_from_handle(process);
    unsafe { CloseHandle(process) };
    Ok(Some(start_time?))
}

#[cfg(windows)]
fn process_start_time_from_handle(
    process: windows_sys::Win32::Foundation::HANDLE,
) -> std::io::Result<u128> {
    use windows_sys::Win32::Foundation::FILETIME;

    let mut creation = FILETIME {
        dwLowDateTime: 0,
        dwHighDateTime: 0,
    };
    let mut exit = FILETIME {
        dwLowDateTime: 0,
        dwHighDateTime: 0,
    };
    let mut kernel = FILETIME {
        dwLowDateTime: 0,
        dwHighDateTime: 0,
    };
    let mut user = FILETIME {
        dwLowDateTime: 0,
        dwHighDateTime: 0,
    };
    let result =
        unsafe { GetProcessTimes(process, &mut creation, &mut exit, &mut kernel, &mut user) };
    if result == 0 {
        return Err(std::io::Error::last_os_error());
    }

    Ok((u128::from(creation.dwHighDateTime) << 32) | u128::from(creation.dwLowDateTime))
}

#[cfg(not(any(target_os = "macos", windows)))]
fn process_executable_path(_pid: NonZeroU32) -> std::io::Result<Option<PathBuf>> {
    Err(std::io::Error::other("unsupported platform"))
}

#[cfg(not(any(target_os = "macos", windows)))]
fn process_start_time(_pid: NonZeroU32) -> std::io::Result<Option<u128>> {
    Err(std::io::Error::other("unsupported platform"))
}

fn sidecar_process_matches(pid: NonZeroU32, expected: &Path) -> std::io::Result<Option<u128>> {
    let start_time = process_start_time(pid)?;
    if start_time.is_none() {
        return Ok(None);
    }
    let Some(actual) = process_executable_path(pid)? else {
        return Ok(None);
    };
    if !paths_match(&actual, expected) {
        return Err(std::io::Error::other("sidecar executable mismatch"));
    }
    Ok(start_time)
}

#[cfg(target_os = "macos")]
fn sidecar_process_group_isolated(pid: NonZeroU32) -> std::io::Result<bool> {
    let process_group = unsafe { libc::getpgid(pid.get() as libc::pid_t) };
    if process_group < 0 {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() == Some(libc::ESRCH) {
            return Ok(false);
        }
        return Err(error);
    }
    Ok(process_group == pid.get() as libc::pid_t)
}

#[cfg(target_os = "macos")]
fn process_group_is_alive(pid: NonZeroU32) -> bool {
    let result = unsafe { libc::kill(-(pid.get() as libc::pid_t), 0) };
    if result == 0 {
        return true;
    }
    std::io::Error::last_os_error().raw_os_error() != Some(libc::ESRCH)
}

#[cfg(target_os = "macos")]
fn signal_process_group(pid: NonZeroU32, signal: libc::c_int) -> std::io::Result<()> {
    if unsafe { libc::kill(-(pid.get() as libc::pid_t), signal) } == 0 {
        return Ok(());
    }
    let error = std::io::Error::last_os_error();
    if error.raw_os_error() == Some(libc::ESRCH) {
        return Ok(());
    }
    Err(error)
}

#[cfg(target_os = "macos")]
fn terminate_macos_process_group(root: NonZeroU32, root_start_time: u128) -> std::io::Result<()> {
    if process_start_time(root)? != Some(root_start_time) || !sidecar_process_group_isolated(root)?
    {
        return Err(std::io::Error::other(
            "sidecar process group is not isolated",
        ));
    }

    signal_process_group(root, libc::SIGTERM)?;
    let deadline = Instant::now() + Duration::from_millis(500);
    while Instant::now() < deadline && process_group_is_alive(root) {
        std::thread::sleep(Duration::from_millis(10));
    }

    if process_group_is_alive(root) {
        signal_process_group(root, libc::SIGKILL)?;
    }
    let deadline = Instant::now() + Duration::from_millis(500);
    while Instant::now() < deadline && process_group_is_alive(root) {
        std::thread::sleep(Duration::from_millis(10));
    }
    if process_group_is_alive(root) {
        return Err(std::io::Error::other("sidecar process group did not exit"));
    }
    Ok(())
}

#[cfg(windows)]
fn terminate_windows_process_tree(
    pid: NonZeroU32,
    expected: &Path,
    expected_start_time: u128,
) -> std::io::Result<()> {
    use windows_sys::Win32::Foundation::{CloseHandle, ERROR_INVALID_PARAMETER};
    use windows_sys::Win32::System::Threading::{
        OpenProcess, TerminateProcess, PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_TERMINATE,
    };

    // The packaged sidecar puts itself in a kill-on-close Job Object before
    // starting the API. Terminating the validated root closes that handle and
    // lets Windows terminate every descendant atomically.
    let access = PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE;
    let process = unsafe { OpenProcess(access, 0, pid.get()) };
    if process.is_null() {
        let error = std::io::Error::last_os_error();
        if error.raw_os_error() == Some(ERROR_INVALID_PARAMETER as i32) {
            return Ok(());
        }
        return Err(error);
    }

    let actual_path = match process_executable_path_from_handle(process) {
        Ok(path) => path,
        Err(error) => {
            unsafe { CloseHandle(process) };
            return Err(error);
        }
    };
    if !paths_match(&actual_path, expected) {
        unsafe { CloseHandle(process) };
        return Err(std::io::Error::other("sidecar executable mismatch"));
    }
    let actual_start_time = match process_start_time_from_handle(process) {
        Ok(start_time) => start_time,
        Err(error) => {
            unsafe { CloseHandle(process) };
            return Err(error);
        }
    };
    if actual_start_time != expected_start_time {
        unsafe { CloseHandle(process) };
        return Err(std::io::Error::other("sidecar process identity changed"));
    }

    let terminated = unsafe { TerminateProcess(process, 1) };
    let error = if terminated == 0 {
        Some(std::io::Error::last_os_error())
    } else {
        None
    };
    unsafe { CloseHandle(process) };
    error.map_or(Ok(()), Err)
}

fn terminate_sidecar_process(
    pid: NonZeroU32,
    expected: &Path,
    expected_start_time: u128,
) -> std::io::Result<()> {
    let Some(start_time) = sidecar_process_matches(pid, expected)? else {
        // The sidecar already exited before cleanup reached it.
        return Ok(());
    };

    if start_time != expected_start_time {
        return Err(std::io::Error::other("sidecar process identity changed"));
    }
    match process_start_time(pid)? {
        None => return Ok(()),
        Some(current_start_time) if current_start_time != start_time => {
            return Err(std::io::Error::other("sidecar process identity changed"));
        }
        Some(_) => {}
    }

    #[cfg(target_os = "macos")]
    {
        return terminate_macos_process_group(pid, start_time);
    }

    #[cfg(windows)]
    {
        return terminate_windows_process_tree(pid, expected, expected_start_time);
    }

    #[cfg(not(any(target_os = "macos", windows)))]
    {
        let _ = (pid, expected, expected_start_time);
        Err(std::io::Error::other("unsupported platform"))
    }
}

#[tauri::command]
fn get_sidecar_process_identity(pid: u32) -> Result<String, String> {
    let pid =
        validate_sidecar_pid(pid).map_err(|_| "Unable to inspect sidecar process".to_string())?;
    let expected =
        expected_sidecar_path().map_err(|_| "Unable to inspect sidecar process".to_string())?;
    let Some(start_time) = sidecar_process_matches(pid, &expected)
        .map_err(|_| "Unable to inspect sidecar process".to_string())?
    else {
        return Err("Unable to inspect sidecar process".to_string());
    };
    #[cfg(target_os = "macos")]
    if !sidecar_process_group_isolated(pid)
        .map_err(|_| "Unable to inspect sidecar process".to_string())?
    {
        return Err("Unable to inspect sidecar process".to_string());
    }
    Ok(start_time.to_string())
}

#[tauri::command]
fn terminate_sidecar_pid(pid: u32, start_time: String) -> Result<(), String> {
    let pid =
        validate_sidecar_pid(pid).map_err(|_| "Unable to stop sidecar process".to_string())?;
    let expected =
        expected_sidecar_path().map_err(|_| "Unable to stop sidecar process".to_string())?;
    let expected_start_time = start_time
        .parse::<u128>()
        .map_err(|_| "Unable to stop sidecar process".to_string())?;
    terminate_sidecar_process(pid, &expected, expected_start_time)
        .map_err(|_| "Unable to stop sidecar process".to_string())
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

    #[test]
    fn sidecar_pid_must_be_non_zero() {
        assert!(validate_sidecar_pid(0).is_err());
        assert_eq!(validate_sidecar_pid(42).unwrap().get(), 42);

        #[cfg(unix)]
        assert!(validate_sidecar_pid(u32::MAX).is_err());
    }

    #[test]
    fn sidecar_path_matching_rejects_unrelated_executables() {
        let expected = Path::new("/Applications/VoidMelody.app/Contents/MacOS/melody-api");
        assert!(paths_match(expected, expected));
        assert!(!paths_match(
            Path::new("/Applications/Other.app/Contents/MacOS/melody-api"),
            expected,
        ));
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
        .invoke_handler(tauri::generate_handler![
            get_runtime_preflight,
            get_sidecar_process_identity,
            terminate_sidecar_pid
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
