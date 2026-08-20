"""Single-slot Voice Lab clone/profile orchestration."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from vieneu_core import VoiceProfileRequest, create_reference_profile

from app.models.custom_voice import CustomVoiceModel

_clone_lock = asyncio.Semaphore(1)


class CloneOrchestrationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class CloneOrchestrator:
    async def create(
        self,
        *,
        session: AsyncSession,
        display_name: str,
        transcript: str,
        consent_given: bool,
        reference_audio_path: Path,
        duration_seconds: float,
        selected_start_seconds: float = 0.0,
        selected_end_seconds: float | None = None,
        quality_score: int | None = None,
        warnings: list[str] | None = None,
        progress: Callable[[str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> CustomVoiceModel:
        def stage(name: str) -> None:
            if progress:
                progress(name)

        if not consent_given:
            raise CloneOrchestrationError("CONSENT_REQUIRED", "Consent is required to create a voice profile.")
        if not display_name.strip():
            raise CloneOrchestrationError("INVALID_NAME", "Voice name is required.")

        async with _clone_lock:
            stage("validating")
            duplicate = await session.scalar(
                select(CustomVoiceModel).where(CustomVoiceModel.display_name == display_name.strip())
            )
            if duplicate:
                raise CloneOrchestrationError("DUPLICATE_NAME", "A voice with this name already exists.")
            if is_cancelled and is_cancelled():
                raise CloneOrchestrationError("CANCELLED", "Voice profile creation was cancelled.")

            stage("preparing_reference")
            try:
                await asyncio.to_thread(
                    create_reference_profile,
                    VoiceProfileRequest(
                        profile_id=str(uuid.uuid4()),
                        reference_audio_path=reference_audio_path,
                        transcript=transcript.strip() or None,
                    ),
                    is_cancelled=is_cancelled,
                )
            except ValueError as exc:
                raise CloneOrchestrationError(
                    getattr(exc, "code", "INVALID_REFERENCE"),
                    getattr(exc, "message", "Reference audio is invalid."),
                ) from exc

            if is_cancelled and is_cancelled():
                raise CloneOrchestrationError("CANCELLED", "Voice profile creation was cancelled.")
            stage("saving")
            voice = CustomVoiceModel(
                id=str(uuid.uuid4()),
                display_name=display_name.strip(),
                reference_audio_path=str(reference_audio_path),
                transcript=transcript.strip() or "[reference audio]",
                consent_given=True,
                consent_version="voice-lab-v1",
                provider_id="vieneu",
                engine_id="v3turbo",
                status="ready",
                duration_seconds=duration_seconds,
                selected_start_seconds=selected_start_seconds,
                selected_end_seconds=selected_end_seconds or duration_seconds,
                quality_score=quality_score,
                analysis_warnings=json.dumps(warnings or []),
            )
            session.add(voice)
            try:
                await session.commit()
                await session.refresh(voice)
            except Exception as exc:
                await session.rollback()
                raise CloneOrchestrationError("DATABASE_ERROR", "Voice profile could not be saved.") from exc
            stage("ready")
            return voice
