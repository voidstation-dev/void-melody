"""Database maintenance, optimization, and cleanup tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.models.audio_cache import AudioSegmentCacheModel

logger = logging.getLogger(__name__)


async def run_pragma_optimize(session: AsyncSession | None = None) -> None:
    """Execute SQLite PRAGMA optimize to refresh query planner statistics."""
    try:
        if session is not None:
            await session.execute(text("PRAGMA optimize"))
        else:
            async with AsyncSessionLocal() as sess:
                await sess.execute(text("PRAGMA optimize"))
        logger.debug("Executed PRAGMA optimize successfully")
    except Exception:
        logger.warning("Failed to run PRAGMA optimize", exc_info=True)


async def run_wal_checkpoint(mode: str = "PASSIVE") -> dict[str, int]:
    """Execute SQLite WAL checkpoint (PASSIVE, FULL, RESTART, TRUNCATE)."""
    try:
        async with AsyncSessionLocal() as sess:
            result = await sess.execute(text(f"PRAGMA wal_checkpoint({mode})"))
            row = result.fetchone()
            if row:
                return {"busy": row[0], "log": row[1], "checkpointed": row[2]}
    except Exception:
        logger.warning("Failed to run wal_checkpoint", exc_info=True)
    return {"busy": 0, "log": 0, "checkpointed": 0}


async def prune_audio_cache(
    *,
    max_bytes: int | None = None,
    ttl_days: int | None = None,
) -> int:
    """Prune audio segment cache based on LRU last_used_at and maximum disk usage."""
    limit_bytes = max_bytes or settings.audio_cache_max_bytes
    limit_days = ttl_days or settings.audio_cache_ttl_days
    deleted_count = 0

    async with AsyncSessionLocal() as session:
        # 1. Prune expired entries past TTL
        if limit_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=limit_days)
            expired_items = (
                await session.scalars(
                    select(AudioSegmentCacheModel).where(
                        AudioSegmentCacheModel.last_used_at < cutoff
                    )
                )
            ).all()

            for item in expired_items:
                if item.audio_path:
                    Path(item.audio_path).unlink(missing_ok=True)
                await session.delete(item)
                deleted_count += 1

            if expired_items:
                await session.commit()

        # 2. Check total size and prune oldest entries if above max_bytes
        total_size = (
            await session.scalar(
                select(func.coalesce(func.sum(AudioSegmentCacheModel.file_size), 0))
            )
        ) or 0

        if total_size > limit_bytes:
            excess = total_size - limit_bytes
            oldest_items = (
                await session.scalars(
                    select(AudioSegmentCacheModel)
                    .order_by(AudioSegmentCacheModel.last_used_at.asc())
                    .limit(100)
                )
            ).all()

            freed = 0
            for item in oldest_items:
                if item.audio_path:
                    Path(item.audio_path).unlink(missing_ok=True)
                freed += item.file_size or 0
                await session.delete(item)
                deleted_count += 1
                if freed >= excess:
                    break

            if oldest_items:
                await session.commit()

    return deleted_count
