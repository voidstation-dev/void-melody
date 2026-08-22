"""Sanitized post-start diagnostics for the desktop API runtime."""

import os
import platform
import shutil
from pathlib import Path

from app.config import settings
from app.services.voice_catalog import voice_catalog


def _has_value(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _port_is_valid(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        port = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return 0 <= port <= 65535


def _data_directory_ready() -> bool:
    try:
        settings.audio_storage_dir.parent.mkdir(parents=True, exist_ok=True)
        return settings.audio_storage_dir.parent.is_dir()
    except OSError:
        return False


def _ffmpeg_ready() -> bool:
    configured = settings.ffmpeg_binary_path
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path.is_file() and os.access(configured_path, os.X_OK)
    return shutil.which(configured) is not None


def _voice_catalog_ready() -> bool:
    try:
        return bool(voice_catalog.list_voices())
    except Exception:  # noqa: BLE001 - diagnostics must remain available
        return False


def build_runtime_report() -> dict[str, object]:
    """Return runtime readiness without exposing configuration values or paths."""
    app_env_ready = _has_value(settings.app_env)
    checks = {
        "APP_ENV": app_env_ready,
        "API_HOST": _has_value(settings.api_host),
        "API_PORT": _port_is_valid(settings.api_port),
        "MELODY_API_TOKEN": (
            not app_env_ready
            or settings.app_env.lower() != "production"
            or _has_value(settings.melody_api_token)
        ),
        "MELODY_DATA_DIR": _data_directory_ready(),
        "MELODY_CATALOG_PATH": settings.capcut_catalog_path.is_file(),
        "ffmpeg": _ffmpeg_ready(),
        "voice_catalog": _voice_catalog_ready(),
    }
    return {
        "status": "ok" if all(checks.values()) else "degraded",
        "platform": platform.system().lower(),
        "architecture": platform.machine().lower(),
        "checks": checks,
    }
