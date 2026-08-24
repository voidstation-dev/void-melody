"""Generic Audio Segment Cache service for deduplicating repeated TTS synthesis."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as database
from app.config import settings
from app.models.audio_cache import AudioSegmentCacheModel

logger = logging.getLogger(__name__)


def get_cache_dir() -> Path:
    return settings.audio_storage_dir / "cache"


def compute_segment_fingerprint(
    *,
    provider_id: str,
    text: str,
    voice_type: str,
    resource_id: str | None = None,
    rate: float = 1.0,
    style: str | None = None,
    voice_revision: str = "v1",
    model_version: str = "default",
) -> str:
    """Generate a deterministic 64-character SHA256 fingerprint for a synthesis request."""
    normalized = "|".join([
        provider_id.strip().lower(),
        model_version.strip().lower(),
        text.strip(),
        voice_type.strip(),
        (resource_id or "").strip(),
        f"{rate:.3f}",
        (style or "").strip().lower(),
        voice_revision.strip(),
    ])
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def lookup_cache(
    fingerprint: str,
    session_factory: Any | None = None,
) -> AudioSegmentCacheModel | None:
    """Look up an existing synthesized audio segment in the cache."""
    if not settings.audio_cache_enabled:
        return None

    factory = session_factory or database.AsyncSessionLocal
    try:
        async with factory() as sess:
            entry = await sess.get(AudioSegmentCacheModel, fingerprint)
            if entry is None:
                return None

            file_path = Path(entry.audio_path)
            if not file_path.is_file():
                await sess.delete(entry)
                await sess.commit()
                return None

            entry.last_used_at = datetime.now(timezone.utc)
            await sess.commit()
            return entry
    except Exception:
        logger.debug("Cache lookup skipped due to session/db error", exc_info=True)
        return None


async def store_cache(
    *,
    fingerprint: str,
    provider_id: str,
    voice_key: str,
    text: str,
    source_audio_path: Path,
    rate: float = 1.0,
    style: str | None = None,
    voice_revision: str = "v1",
    mime_type: str = "audio/mpeg",
    audio_duration: float | None = None,
    session_factory: Any | None = None,
) -> AudioSegmentCacheModel | None:
    """Store a newly synthesized audio segment into cache storage and database."""
    if not settings.audio_cache_enabled or not source_audio_path.is_file():
        return None

    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    extension = source_audio_path.suffix or ".mp3"
    target_cache_file = cache_dir / f"{fingerprint}{extension}"

    try:
        await asyncio.to_thread(shutil.copy2, str(source_audio_path), str(target_cache_file))
        file_size = target_cache_file.stat().st_size
    except Exception:
        logger.warning("Failed copying audio to cache storage", exc_info=True)
        return None

    text_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    factory = session_factory or database.AsyncSessionLocal

    try:
        async with factory() as sess:
            existing = await sess.get(AudioSegmentCacheModel, fingerprint)
            if existing is not None:
                existing.last_used_at = datetime.now(timezone.utc)
                existing.audio_path = str(target_cache_file)
                existing.file_size = file_size
                await sess.commit()
                return existing

            cache_entry = AudioSegmentCacheModel(
                fingerprint=fingerprint,
                provider_id=provider_id,
                provider_version="v1",
                voice_key=voice_key,
                voice_revision=voice_revision,
                text_hash=text_hash,
                style=style,
                rate=rate,
                audio_path=str(target_cache_file),
                mime_type=mime_type,
                audio_duration=audio_duration,
                file_size=file_size,
            )
            sess.add(cache_entry)
            try:
                await sess.commit()
            except Exception:
                await sess.rollback()
                entry = await sess.get(AudioSegmentCacheModel, fingerprint)
                if entry:
                    return entry
            return cache_entry
    except Exception:
        logger.debug("Cache store skipped due to session/db error", exc_info=True)
        return None
