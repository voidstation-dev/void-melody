from sidecar_entrypoint import isolate_sidecar_environment


def test_isolation_removes_host_secrets_and_preserves_desktop_runtime_contract():
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
    }

    for name in (
        "HF_TOKEN",
        "HUGGINGFACE_HUB_TOKEN",
        "TAURI_SIGNING_PRIVATE_KEY",
        "TAURI_SIGNING_PRIVATE_KEY_PASSWORD",
    ):
        assert name not in isolated
