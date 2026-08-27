"""Dedicated resolver for OmniVoice designed voices.

This resolver does NOT reuse voice_resolver.py, which is built around
VieNeu enrollment artifacts (speaker_emb, ref_codes, reference_audio_path).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.omnivoice_voice import OmniVoiceVoiceModel

logger = logging.getLogger(__name__)


class OmniVoiceResolutionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ResolvedOmniVoice:
    id: str
    display_name: str
    provider_id: str
    engine_id: str
    voice_kind: str
    status: str
    prompt_artifact_path: str
    prompt_format_version: str
    model_id: str
    model_revision: str
    engine_version: str | None
    sample_rate: int | None
    voice_revision: str | None
    design_prompt: str | None = None
    compiled_instruction: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "provider_id": self.provider_id,
            "engine_id": self.engine_id,
            "voice_kind": self.voice_kind,
            "status": self.status,
            "prompt_artifact_path": self.prompt_artifact_path,
            "prompt_format_version": self.prompt_format_version,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "engine_version": self.engine_version,
            "sample_rate": self.sample_rate,
            "voice_revision": self.voice_revision,
            "design_prompt": self.design_prompt,
            "compiled_instruction": self.compiled_instruction,
        }


async def resolve_omnivoice_voice(
    session: AsyncSession,
    voice_id: str,
) -> ResolvedOmniVoice:
    """Resolve a persisted OmniVoice voice by id.

    Raises:
        OmniVoiceResolutionError: if the voice does not exist, is not ready,
            or its prompt artifact is missing.
    """
    voice = await session.scalar(
        select(OmniVoiceVoiceModel).where(OmniVoiceVoiceModel.id == voice_id)
    )
    if voice is None:
        raise OmniVoiceResolutionError(
            "VOICE_NOT_FOUND",
            f"OmniVoice voice '{voice_id}' does not exist.",
        )

    if voice.status != "ready":
        raise OmniVoiceResolutionError(
            "VOICE_NOT_READY",
            f"OmniVoice voice '{voice_id}' is not ready for synthesis.",
        )

    if not voice.prompt_artifact_path:
        raise OmniVoiceResolutionError(
            "VOICE_PROMPT_MISSING",
            f"OmniVoice voice '{voice_id}' has no saved VoiceClonePrompt.",
        )

    prompt_path = Path(voice.prompt_artifact_path)
    if not prompt_path.is_file():
        raise OmniVoiceResolutionError(
            "VOICE_PROMPT_MISSING",
            f"OmniVoice voice '{voice_id}' prompt artifact is missing at {prompt_path}.",
        )

    return ResolvedOmniVoice(
        id=voice.id,
        display_name=voice.display_name,
        provider_id=voice.provider_id,
        engine_id=voice.engine_id,
        voice_kind=voice.voice_kind,
        status=voice.status,
        prompt_artifact_path=str(prompt_path),
        prompt_format_version=voice.prompt_format_version,
        model_id=voice.model_id,
        model_revision=voice.model_revision,
        engine_version=voice.engine_version,
        sample_rate=voice.sample_rate,
        voice_revision=voice.voice_revision,
        design_prompt=voice.design_prompt,
        compiled_instruction=voice.compiled_instruction,
    )
