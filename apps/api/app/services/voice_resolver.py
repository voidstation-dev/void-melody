import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_voice import CustomVoiceModel
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.services.voice_catalog import voice_catalog
from app.services.voice_profile_artifacts import load_enrollment_artifact

from app.services.prepared_voice import PreparedVoice

logger = logging.getLogger(__name__)


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
    # For V3 Enrollment v2 this is profile metadata only — NOT active model
    # conditioning. A future transcript-conditioned engine may consume it.
    prompt_text: str | None = None
    profile_format_version: str = "reference-v1"
    speaker_emb: np.ndarray | None = None
    ref_codes: np.ndarray | None = None
    clone_mode: str = "fidelity"

    def to_prepared_voice(self) -> PreparedVoice:
        return PreparedVoice(
            voice_type=self.voice_type,
            provider_id=self.provider_id,
            source=self.source,
            voice_revision=self.voice_revision,
            speaker_emb=self.speaker_emb,
            ref_codes=self.ref_codes,
            clone_mode=self.clone_mode,
            profile_format_version=self.profile_format_version,
            reference_audio_path=self.reference_audio_path,
            prompt_text=self.prompt_text,
        )


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
    if custom:
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

        speaker_emb: np.ndarray | None = None
        ref_codes: np.ndarray | None = None
        format_version = custom.profile_format_version or "reference-v1"

        if custom.enrollment_artifact_path and Path(custom.enrollment_artifact_path).is_file():
            try:
                speaker_emb, ref_codes, _ = load_enrollment_artifact(Path(custom.enrollment_artifact_path))
                format_version = "vieneu-enrollment-v2"
            except Exception as exc:
                logger.warning("Failed loading v2 artifact for voice %s, fallback to v1: %s", custom.id, exc)

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
            profile_format_version=format_version,
            speaker_emb=speaker_emb,
            ref_codes=ref_codes,
            clone_mode=custom.clone_mode or "fidelity",
        )

        # Store in LRU cache
        if len(_custom_voice_cache) >= _MAX_CACHE_SIZE:
            oldest_key = min(_custom_voice_cache.keys(), key=lambda k: _custom_voice_cache[k][0])
            _custom_voice_cache.pop(oldest_key, None)
        _custom_voice_cache[voice_type] = (now, resolved)

        return resolved

    # Fall back to OmniVoice designed voices.
    omni = await session.scalar(
        select(OmniVoiceVoiceModel).where(OmniVoiceVoiceModel.id == voice_type)
    )
    if omni:
        if omni.status != "ready":
            raise VoiceResolutionError(
                "VOICE_NOT_READY",
                "Selected OmniVoice voice is not ready for synthesis.",
            )
        if not omni.prompt_artifact_path or not Path(omni.prompt_artifact_path).is_file():
            raise VoiceResolutionError(
                "OMNI_VOICE_PROMPT_MISSING",
                "Selected OmniVoice voice prompt artifact is missing.",
            )
        return ResolvedVoice(
            voice_type=omni.id,
            display_name=omni.display_name,
            language_code="vi-VN",
            resource_id=None,
            provider_id=omni.provider_id,
            source="custom",
            status=omni.status,
            voice_revision=omni.voice_revision or "v1",
            reference_audio_path=omni.prompt_artifact_path,
            prompt_text=omni.compiled_instruction,
            profile_format_version=omni.prompt_format_version,
            speaker_emb=None,
            ref_codes=None,
            clone_mode="fidelity",
        )

    raise VoiceResolutionError(
        "VOICE_NOT_FOUND",
        "Selected voice type does not exist in the catalog.",
    )
