import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.v1.router import api_router
from app.config import settings
from app.database import AsyncSessionLocal
from app.db.maintenance import prune_audio_cache, run_pragma_optimize
from app.middleware.local_auth import LocalAuthMiddleware, validate_runtime_security
from app.models.custom_voice import CustomVoiceModel
from app.services.plan_enforcement import PlanFeatureNotAllowedError
from app.services.audio_cleanup import cleanup_stale_temp_files
from app.services.audio_storage import close_http_client
from app.services.database_migrations import run_database_migrations
from app.services.job_recovery import recover_jobs
from app.services.logging_config import configure_logging
from app.services.raw_response_storage import cleanup_stale_raw_responses
from app.services.script_render_service import recover_interrupted_script_renders
from app.services.vieneu_bootstrap import bootstrap_vieneu_runtime
from app.services.voice_artifact_cleanup import cleanup_orphan_voice_artifacts
from app.workers.queue_manager import queue_manager
from app.workers.script_render_queue import script_render_queue

logger = logging.getLogger(__name__)


async def _run_background_housekeeping():
    """Background startup task to warm up models and cleanup without blocking API boot."""
    # 1. Warm up VieNeu runtime in background
    if settings.voice_lab_enabled:
        try:
            await bootstrap_vieneu_runtime(settings.vieneu_hf_home)
        except Exception:  # noqa: BLE001
            logger.exception(
                "VieNeu model bootstrap failed; voice cloning will remain unavailable"
            )

    # 2. Asynchronously cleanup stale artifacts
    try:
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
        await prune_audio_cache()
        await run_pragma_optimize()
    except Exception:  # noqa: BLE001
        logger.exception("Background housekeeping encountered an error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    validate_runtime_security()
    await run_database_migrations()

    recovered_jobs = await recover_jobs()
    await recover_interrupted_script_renders()
    await queue_manager.start()
    await script_render_queue.start()

    for item in recovered_jobs:
        await queue_manager.enqueue(
            item.job_id,
            batch_position=item.batch_position,
            provider_id=item.provider_id,
        )

    # Launch background housekeeping & warmup without blocking API readiness
    housekeeping_task = asyncio.create_task(_run_background_housekeeping())

    try:
        yield
    finally:
        housekeeping_task.cancel()
        await queue_manager.stop()
        await script_render_queue.stop()
        await close_http_client()
        try:
            await run_pragma_optimize()
        except Exception:
            pass


app = FastAPI(title="CapVoice Studio API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(PlanFeatureNotAllowedError)
async def plan_feature_not_allowed_handler(_, exc: PlanFeatureNotAllowedError):
    return JSONResponse(
        status_code=403,
        content={
            "error_code": "PLAN_FEATURE_NOT_ALLOWED",
            "feature": exc.feature,
            "message": exc.detail,
        },
    )


app.add_middleware(LocalAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID", "X-Melody-Token", "X-License-Key"],
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import multiprocessing
    import sys

    import uvicorn

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True, write_through=True)

    # Required for PyInstaller multi-processing support
    multiprocessing.freeze_support()

    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )
    server = uvicorn.Server(config)

    original_startup = server.startup

    async def custom_startup(sockets=None):
        await original_startup(sockets=sockets)
        for s in getattr(server, "servers", []):
            for sock in getattr(s, "sockets", []):
                addr = sock.getsockname()
                if isinstance(addr, tuple) and len(addr) >= 2:
                    print(f"Listening on {addr[0]}:{addr[1]}", flush=True)
                    print(f"Uvicorn running on http://{addr[0]}:{addr[1]}", flush=True)

    server.startup = custom_startup
    server.run()
