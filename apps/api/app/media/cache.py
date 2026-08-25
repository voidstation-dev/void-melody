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


from collections.abc import Sequence
from sqlalchemy import select, update


async def lookup_cache(
    fingerprint: str,
    *,
    touch_db: bool = True,
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

            if touch_db:
                entry.last_used_at = datetime.now(timezone.utc)
                await sess.commit()
            return entry
    except Exception:
        logger.debug("Cache lookup skipped due to session/db error", exc_info=True)
        return None


async def batch_touch_cache_fingerprints(
    fingerprints: Sequence[str],
    session_factory: Any | None = None,
) -> None:
    """Update last_used_at for multiple cached fingerprints in a single transaction."""
    if not settings.audio_cache_enabled or not fingerprints:
        return

    unique_fps = list(set(fingerprints))
    factory = session_factory or database.AsyncSessionLocal
    try:
        async with factory() as sess:
            await sess.execute(
                update(AudioSegmentCacheModel)
                .where(AudioSegmentCacheModel.fingerprint.in_(unique_fps))
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await sess.commit()
    except Exception:
        logger.debug("Batch cache touch failed", exc_info=True)


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


async def batch_store_cache_entries(
    entries: Sequence[dict[str, Any]],
    session_factory: Any | None = None,
) -> None:
    """Store multiple newly synthesized audio segments into cache storage and database in one transaction."""
    if not settings.audio_cache_enabled or not entries:
        return

    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    items_to_persist = []
    for entry_data in entries:
        source_path = Path(entry_data["source_audio_path"])
        if not source_path.is_file():
            continue
        fp = entry_data["fingerprint"]
        ext = source_path.suffix or ".mp3"
        target_file = cache_dir / f"{fp}{ext}"
        try:
            await asyncio.to_thread(shutil.copy2, str(source_path), str(target_file))
            items_to_persist.append((entry_data, target_file, target_file.stat().st_size))
        except Exception:
            logger.warning("Failed copying audio to cache storage for fp %s", fp, exc_info=True)

    if not items_to_persist:
        return

    factory = session_factory or database.AsyncSessionLocal
    try:
        async with factory() as sess:
            for item, target_file, file_size in items_to_persist:
                fp = item["fingerprint"]
                existing = await sess.get(AudioSegmentCacheModel, fp)
                if existing is not None:
                    existing.last_used_at = datetime.now(timezone.utc)
                    existing.audio_path = str(target_file)
                    existing.file_size = file_size
                else:
                    text_hash = hashlib.sha256(item["text"].strip().encode("utf-8")).hexdigest()
                    cache_entry = AudioSegmentCacheModel(
                        fingerprint=fp,
                        provider_id=item["provider_id"],
                        provider_version="v1",
                        voice_key=item["voice_key"],
                        voice_revision=item.get("voice_revision", "v1"),
                        text_hash=text_hash,
                        style=item.get("style"),
                        rate=item.get("rate", 1.0),
                        audio_path=str(target_file),
                        mime_type=item.get("mime_type", "audio/mpeg"),
                        audio_duration=item.get("audio_duration"),
                        file_size=file_size,
                    )
                    sess.add(cache_entry)
            await sess.commit()
    except Exception:
        logger.debug("Batch cache store failed", exc_info=True)
