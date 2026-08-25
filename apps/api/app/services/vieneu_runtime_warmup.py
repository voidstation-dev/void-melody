"""Background lazy warmup for the VieNeu model and voice resolution artifacts."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from vieneu_core.engine import ModelManager
from app.config import settings
from app.database import AsyncSessionLocal
from app.services.vieneu_resource_governor import vieneu_governor
from app.services.voice_resolver import resolve_voice

logger = logging.getLogger(__name__)

_warmup_lock = asyncio.Lock()
_warmed_up = False


async def warm_vieneu_background(voice_type: str | None = None) -> None:
    """Asynchronously initialize the VieNeu engine and cache voice profile without blocking the API."""
    if not settings.vieneu_background_warmup_enabled:
        return

    global _warmed_up
    async with _warmup_lock:
        try:
            # 1. Warm governor & model manager
            await vieneu_governor.initialize()
            manager = ModelManager()
            if not manager.is_loaded():
                logger.info("Starting background VieNeu engine warmup...")
                await manager.get_engine()
                logger.info("Background VieNeu engine warmup complete.")

            # 2. Warm voice artifact if custom voice specified
            if voice_type:
                try:
                    async with AsyncSessionLocal() as session:
                        await resolve_voice(session, voice_type)
                except Exception:
                    logger.debug("Warmup voice resolution skipped for %s", voice_type)

            _warmed_up = True
        except Exception:
            logger.warning("Background VieNeu warmup encountered non-fatal error", exc_info=True)
