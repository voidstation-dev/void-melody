import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.router import api_router
from app.config import settings
from app.database import AsyncSessionLocal
from app.middleware.local_auth import LocalAuthMiddleware, validate_runtime_security
from app.services.audio_cleanup import cleanup_stale_temp_files
from app.services.audio_storage import close_http_client
from app.services.database_migrations import run_database_migrations
from app.services.job_recovery import recover_jobs
from app.services.logging_config import configure_logging
from app.services.raw_response_storage import cleanup_stale_raw_responses
from app.services.voice_artifact_cleanup import cleanup_orphan_voice_artifacts
from app.services.vieneu_bootstrap import bootstrap_vieneu_runtime
from app.services.script_render_service import recover_interrupted_script_renders
from app.services.trial_service import get_runtime_trial_service
from app.services.trial_domain import TrialStatus
from app.models.custom_voice import CustomVoiceModel
from app.workers.queue_manager import queue_manager
from app.workers.script_render_queue import script_render_queue
from app.exceptions import TrialNotAllowedError
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    validate_runtime_security()
    trial_status = get_runtime_trial_service().get_status()
    if settings.app_env.lower() == "production" and trial_status.status is TrialStatus.CORRUPTED:
        raise RuntimeError("TRIAL_STATE_CORRUPTED: local trial state could not be verified")
    await run_database_migrations()
    if settings.voice_lab_enabled:
        try:
            await bootstrap_vieneu_runtime(settings.vieneu_hf_home)
        except Exception:  # noqa: BLE001 - keep the API usable if the network is unavailable
            logger.exception(
                "VieNeu model bootstrap failed; voice cloning will remain unavailable"
            )
    async with AsyncSessionLocal() as session:
        known_reference_paths = await session.scalars(
            select(CustomVoiceModel.reference_audio_path).where(
                CustomVoiceModel.status.in_(["creating", "ready"])
            )
        )
        await asyncio.to_thread(
            cleanup_orphan_voice_artifacts,
            settings.custom_voices_dir,
            known_paths={Path(path) for path in known_reference_paths if path},
        )
    await asyncio.to_thread(
        cleanup_stale_temp_files,
        audio_dir=settings.audio_storage_dir,
        older_than_seconds=3_600,
    )
    await asyncio.to_thread(
        cleanup_stale_raw_responses,
        settings.raw_response_dir,
        older_than_seconds=settings.raw_provider_response_retention_seconds,
    )
    recovered_jobs = await recover_jobs()
    await recover_interrupted_script_renders()
    await queue_manager.start()
    await script_render_queue.start()
    for job_id, batch_pos in recovered_jobs:
        await queue_manager.enqueue(job_id, batch_position=batch_pos)
    try:
        yield
    finally:
        await queue_manager.stop()
        await script_render_queue.stop()
        await close_http_client()


app = FastAPI(title="CapVoice Studio API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(TrialNotAllowedError)
async def trial_not_allowed_handler(_, exc: TrialNotAllowedError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "code": exc.code,
            "detail": {"code": exc.code, "message": exc.message},
        },
    )

app.add_middleware(LocalAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID", "X-Melody-Token"],
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import multiprocessing
    import sys

    import uvicorn

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)

    # Required for PyInstaller multi-processing support
    multiprocessing.freeze_support()
    logging.getLogger(__name__).info(
        "Uvicorn starting on http://%s:%s",
        settings.api_host,
        settings.api_port,
    )
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )
