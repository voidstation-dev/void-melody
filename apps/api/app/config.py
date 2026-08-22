import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Helper to get paths
_data_dir = Path(os.environ.get("MELODY_DATA_DIR", "../../data"))
_data_dir.mkdir(parents=True, exist_ok=True)
_catalog_path = Path(
    os.environ.get("MELODY_CATALOG_PATH", "../../vendor/capcut-tts-api/Voice.json")
)


class Settings(BaseSettings):
    app_env: str = "development"
    voice_lab_enabled: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = int(os.environ.get("API_PORT", "8000"))
    melody_api_token: str | None = None
    license_key: str | None = os.environ.get("MELODY_LICENSE_KEY")
    trial_mode: str = os.environ.get("MELODY_TRIAL_MODE", "auto")
    trial_integrity_key: str | None = os.environ.get("MELODY_TRIAL_INTEGRITY_KEY")
    trial_state_path: Path = Field(default=_data_dir / "trial-state-v1.json")
    cors_origins: list[str] = ["*"]  # Allow electron origins like file:// or app://
    database_url: str = f"sqlite+aiosqlite:///{_data_dir}/app.db"
    vieneu_hf_home: Path = Path(
        os.environ.get("VIENEU_HF_HOME", str(_data_dir / "models"))
    )
    audio_storage_dir: Path = _data_dir / "audio"
    custom_voices_dir: Path = _data_dir / "voices"
    preview_storage_dir: Path = _data_dir / "previews"
    raw_response_dir: Path = _data_dir / "raw-responses"
    capcut_catalog_path: Path = _catalog_path
    tts_queue_concurrency: int = 3
    tts_chunk_concurrency: int = 1
    tts_max_text_chars: int = 50000
    tts_max_chunks_per_job: int = 120
    tts_max_batch_files: int = 50
    tts_max_batch_total_chars: int = 500000
    tts_min_rate: float = 0.5
    tts_max_rate: float = 2.0
    tts_provider_timeout_seconds: float = 90.0
    vieneu_clone_timeout_seconds: float = 180.0
    tts_max_auto_retries: int = 2
    tts_retry_base_delay_seconds: float = 2.0
    tts_apply_rate_with_ffmpeg: bool = False
    tts_circuit_breaker_failure_threshold: int = 5
    tts_circuit_breaker_window_seconds: float = 60.0
    tts_circuit_breaker_cooldown_seconds: float = 30.0
    tts_audio_max_bytes: int = 52428800
    tts_progress_commit_interval_seconds: float = 1.0
    tts_progress_commit_step_percent: int = 5
    tts_queue_shutdown_grace_seconds: float = 15.0
    save_raw_provider_responses: bool = False
    raw_provider_response_retention_seconds: float = 604800.0
    log_level: str = "INFO"

    @property
    def ffmpeg_binary_path(self) -> str:
        """Finds ffmpeg sidecar or fallback to PATH"""
        import sys
        if getattr(sys, 'frozen', False):
            ext = ".exe" if os.name == "nt" else ""
            bundled = os.path.join(os.path.dirname(sys.executable), f"ffmpeg{ext}")
            if os.path.exists(bundled):
                return bundled
        return os.environ.get("FFMPEG_BINARY_PATH", "ffmpeg")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
