"""Resolve preset and custom voice IDs into one queue-safe descriptor with LRU caching."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_voice import CustomVoiceModel
from app.services.voice_catalog import voice_catalog


@dataclass(frozen=True)
class ResolvedVoice:
    voice_type: str
    display_name: str
    language_code: str
    resource_id: str | None
    provider_id: str
    source: str  # "preset" | "custom"
    status: str
    voice_revision: str = "unknown"
    reference_audio_path: str | None = None
    prompt_text: str | None = None


class VoiceResolutionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# In-memory LRU cache for custom voice resolution (TTL 60s, max 100 entries)
_custom_voice_cache: dict[str, tuple[float, ResolvedVoice]] = {}
_CACHE_TTL_SECONDS = 60.0
_MAX_CACHE_SIZE = 100


def invalidate_voice_cache(voice_id: str | None = None) -> None:
    """Invalidate cached custom voice resolutions."""
    if voice_id:
        _custom_voice_cache.pop(voice_id, None)
    else:
        _custom_voice_cache.clear()


async def resolve_voice(session: AsyncSession, voice_type: str) -> ResolvedVoice:
    """Resolve a preset or ready custom voice for both single and batch jobs."""

    preset = voice_catalog.get_voice(voice_type)
    if preset:
        return ResolvedVoice(
            voice_type=preset.voice_type,
            display_name=preset.display_name,
            language_code=preset.language_code,
            resource_id=preset.resource_id,
            provider_id=preset.provider_id,
            source="preset",
            status="ready",
            voice_revision="preset:vieneu-v3turbo",
        )

    # Check in-memory cache for custom voice
    now = time.monotonic()
    if voice_type in _custom_voice_cache:
        cached_time, cached_resolved = _custom_voice_cache[voice_type]
        if now - cached_time < _CACHE_TTL_SECONDS:
            if cached_resolved.reference_audio_path and Path(cached_resolved.reference_audio_path).is_file():
                return cached_resolved

    custom = await session.scalar(
        select(CustomVoiceModel).where(CustomVoiceModel.id == voice_type)
    )
    if not custom:
        raise VoiceResolutionError(
            "VOICE_NOT_FOUND",
            "Selected voice type does not exist in the catalog.",
        )
    if custom.status != "ready":
        raise VoiceResolutionError(
            "VOICE_NOT_READY",
            "Selected custom voice is not ready for synthesis.",
        )
    if not custom.reference_audio_path or not Path(custom.reference_audio_path).is_file():
        raise VoiceResolutionError(
            "VOICE_REFERENCE_MISSING",
            "Selected custom voice reference audio is missing.",
        )

    resolved = ResolvedVoice(
        voice_type=custom.id,
        display_name=custom.display_name,
        language_code="vi-VN",
        resource_id=None,
        provider_id=custom.provider_id,
        source="custom",
        status=custom.status,
        voice_revision=(
            custom.updated_at.isoformat()
            if custom.updated_at
            else f"reference:{Path(custom.reference_audio_path).stat().st_mtime_ns}"
        ),
        reference_audio_path=custom.reference_audio_path,
        prompt_text=custom.transcript,
    )

    # Store in LRU cache
    if len(_custom_voice_cache) >= _MAX_CACHE_SIZE:
        oldest_key = min(_custom_voice_cache.keys(), key=lambda k: _custom_voice_cache[k][0])
        _custom_voice_cache.pop(oldest_key, None)
    _custom_voice_cache[voice_type] = (now, resolved)

    return resolved
