import sidecar_entrypoint

from sidecar_entrypoint import isolate_sidecar_environment


def test_isolation_preserves_required_runtime_state_and_removes_host_configuration():
    runtime_environment = {
        "PYTHONUNBUFFERED": "1",
        "APP_ENV": "production",
        "API_HOST": "127.0.0.1",
        "API_PORT": "0",
        "MELODY_API_TOKEN": "runtime-token",
        "MELODY_DATA_DIR": "/app-data",
        "MELODY_CATALOG_PATH": "/resources/bin/Voice.json",
        "VIENEU_HF_HOME": "/app-data/models",
        "HF_HOME": "/app-data/models",
        "TTS_APPLY_RATE_WITH_FFMPEG": "true",
        "TTS_QUEUE_CONCURRENCY": "1",
        "TTS_CHUNK_CONCURRENCY": "1",
        "_PYI_ARCHIVE_FILE": "/Applications/Void Melody.app/Contents/MacOS/melody-api",
        "_PYI_APPLICATION_HOME_DIR": "/var/folders/test/_MEI12345",
        "_PYI_PARENT_PROCESS_LEVEL": "1",
        "_PYI_SPLASH_IPC": "0",
        "_PYI_FUTURE_RUNTIME_STATE": "preserve-all-private-state",
        "PYINSTALLER_RESET_ENVIRONMENT": "1",
        "SystemRoot": "C:\\Windows",
        "windir": "C:\\Windows",
        "Path": "C:\\Windows\\System32",
        "TEMP": "C:\\Users\\melody\\AppData\\Local\\Temp",
        "TMP": "C:\\Users\\melody\\AppData\\Local\\Temp",
        "TMPDIR": "/var/folders/test/T",
        "HOME": "/Users/melody",
        "USERPROFILE": "C:\\Users\\melody",
        "COMSPEC": "C:\\Windows\\System32\\cmd.exe",
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "HF_TOKEN": "host-huggingface-token",
        "HUGGINGFACE_HUB_TOKEN": "host-hub-token",
        "TAURI_SIGNING_PRIVATE_KEY": "host-signing-key",
        "TAURI_SIGNING_PRIVATE_KEY_PASSWORD": "host-signing-password",
        "UNRELATED_HOST_CONFIGURATION": "do-not-pass-through",
    }

    isolated = isolate_sidecar_environment(runtime_environment)

    assert isolated == {
        "PYTHONUNBUFFERED": "1",
        "APP_ENV": "production",
        "API_HOST": "127.0.0.1",
        "API_PORT": "0",
        "MELODY_API_TOKEN": "runtime-token",
        "MELODY_DATA_DIR": "/app-data",
        "MELODY_CATALOG_PATH": "/resources/bin/Voice.json",
        "VIENEU_HF_HOME": "/app-data/models",
        "HF_HOME": "/app-data/models",
        "TTS_APPLY_RATE_WITH_FFMPEG": "true",
        "TTS_QUEUE_CONCURRENCY": "1",
        "TTS_CHUNK_CONCURRENCY": "1",
        "_PYI_ARCHIVE_FILE": "/Applications/Void Melody.app/Contents/MacOS/melody-api",
        "_PYI_APPLICATION_HOME_DIR": "/var/folders/test/_MEI12345",
        "_PYI_PARENT_PROCESS_LEVEL": "1",
        "_PYI_SPLASH_IPC": "0",
        "_PYI_FUTURE_RUNTIME_STATE": "preserve-all-private-state",
        "PYINSTALLER_RESET_ENVIRONMENT": "1",
        "SystemRoot": "C:\\Windows",
        "windir": "C:\\Windows",
        "Path": "C:\\Windows\\System32",
        "TEMP": "C:\\Users\\melody\\AppData\\Local\\Temp",
        "TMP": "C:\\Users\\melody\\AppData\\Local\\Temp",
        "TMPDIR": "/var/folders/test/T",
        "HOME": "/Users/melody",
        "USERPROFILE": "C:\\Users\\melody",
        "COMSPEC": "C:\\Windows\\System32\\cmd.exe",
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
    }

    for name in (
        "HF_TOKEN",
        "HUGGINGFACE_HUB_TOKEN",
        "TAURI_SIGNING_PRIVATE_KEY",
        "TAURI_SIGNING_PRIVATE_KEY_PASSWORD",
        "UNRELATED_HOST_CONFIGURATION",
    ):
        assert name not in isolated


def test_main_isolates_before_dynamically_loading_app_main(monkeypatch):
    environment = {
        "MELODY_API_TOKEN": "runtime-token",
        "_PYI_ARCHIVE_FILE": "/Applications/Void Melody.app/Contents/MacOS/melody-api",
        "SystemRoot": "C:\\Windows",
        "PATH": "C:\\Windows\\System32",
        "HF_TOKEN": "host-huggingface-token",
        "UNRELATED_HOST_CONFIGURATION": "do-not-pass-through",
    }
    loaded_modules = []

    def capture_dynamic_load(module_name, run_name):
        loaded_modules.append((module_name, run_name, dict(environment)))

    monkeypatch.setattr(sidecar_entrypoint.os, "environ", environment)
    monkeypatch.setattr(sidecar_entrypoint.runpy, "run_module", capture_dynamic_load)

    sidecar_entrypoint.main()

    assert loaded_modules == [
        (
            "app.main",
            "__main__",
            {
                "MELODY_API_TOKEN": "runtime-token",
                "_PYI_ARCHIVE_FILE": "/Applications/Void Melody.app/Contents/MacOS/melody-api",
                "SystemRoot": "C:\\Windows",
                "PATH": "C:\\Windows\\System32",
            },
        )
    ]


def test_main_fails_closed_when_packaged_process_isolation_fails(monkeypatch):
    loaded_modules = []

    monkeypatch.setattr(sidecar_entrypoint, "_isolate_packaged_process_tree", lambda: False)
    monkeypatch.setattr(
        sidecar_entrypoint.runpy,
        "run_module",
        lambda *args, **kwargs: loaded_modules.append((args, kwargs)),
    )

    try:
        sidecar_entrypoint.main()
    except RuntimeError as error:
        assert str(error) == "Unable to isolate packaged sidecar process tree"
    else:
        raise AssertionError("packaged sidecar should fail closed")

    assert loaded_modules == []
