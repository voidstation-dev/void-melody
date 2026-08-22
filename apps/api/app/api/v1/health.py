import asyncio
import os
import signal
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.voice_catalog import voice_catalog
from app.workers.queue_manager import queue_manager

router = APIRouter()
SHUTDOWN_DELAY_SECONDS = 0.05


def _liveness_payload() -> dict[str, str]:
    return {"status": "ok", "service": "capvoice-api"}


@router.get("/health")
async def health_check():
    return _liveness_payload()


@router.get("/health/live")
async def liveness_check():
    return _liveness_payload()


def schedule_process_shutdown() -> None:
    """Ask the PyInstaller child process to exit after the response is sent."""

    loop = asyncio.get_running_loop()
    loop.call_later(
        SHUTDOWN_DELAY_SECONDS,
        os.kill,
        os.getpid(),
        signal.SIGTERM,
    )


@router.post("/health/shutdown", status_code=202)
async def shutdown_sidecar():
    schedule_process_shutdown()
    return {"status": "shutting_down"}


async def _database_ready() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


def _audio_directory_ready() -> bool:
    try:
        settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=settings.audio_storage_dir,
            prefix=".readiness-",
        )
        os.close(descriptor)
        Path(temporary_name).unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _ffmpeg_ready() -> bool:
    configured = settings.ffmpeg_binary_path
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path.is_file() and os.access(configured_path, os.X_OK)
    return shutil.which(configured) is not None


@router.get("/health/ready")
async def readiness_check():
    database_ok = await _database_ready()
    try:
        voice_count = len(voice_catalog.list_voices())
        catalog_ok = voice_count > 0
    except Exception:  # noqa: BLE001
        voice_count = 0
        catalog_ok = False

    queue = queue_manager.health_snapshot()
    queue_ok = bool(
        queue["accepting_jobs"] and queue["workers_alive"] == queue["worker_count"]
    )
    circuit = queue["circuit_breaker"]
    circuit_ok = circuit["state"] != "open"
    checks = {
        "database": database_ok,
        "queue": queue_ok,
        "voice_catalog": catalog_ok,
        "audio_directory": _audio_directory_ready(),
        "ffmpeg": _ffmpeg_ready(),
        "circuit_breaker": circuit_ok,
    }
    ready = all(checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "degraded",
            "service": "capvoice-api",
            "checks": checks,
            "queueDepth": queue["queue_depth"],
            "workersAlive": queue["workers_alive"],
            "voiceCount": voice_count,
            "circuitBreaker": circuit,
        },
    )
