"""Single-slot Voice Lab clone/profile orchestration (Enrollment v2)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from vieneu_core import create_reference_profile
from vieneu_core.engine import ModelManager

from app.config import settings
from app.models.custom_voice import CustomVoiceModel
from app.services.vieneu_enrollment import VieneuEnrollmentService
from app.services.voice_analysis import VoiceAnalysis
from app.services.voice_reference_processor import process_voice_reference
from app.services.voice_similarity import synthesize_calibration

logger = logging.getLogger(__name__)
_clone_lock = asyncio.Semaphore(1)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloneOrchestrationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class CloneOrchestrator:
    def __init__(
        self,
        *,
        model_manager: ModelManager | None = None,
        preflight: Callable[[Path], Awaitable[None]] | None = None,
    ) -> None:
        self.manager = model_manager or ModelManager()
        self._preflight = preflight

    async def create(
        self,
        *,
        session: AsyncSession,
        display_name: str,
        transcript: str,
        consent_given: bool,
        source_audio_path: Path | None = None,
        reference_audio_path: Path | None = None,
        duration_seconds: float,
        source_duration_seconds: float | None = None,
        reference_duration_seconds: float | None = None,
        selected_start_seconds: float = 0.0,
        selected_end_seconds: float | None = None,
        quality_score: int | None = None,
        warnings: list[str] | None = None,
        denoise_mode: str = "auto",
        clone_mode: str = "fidelity",
        analysis: VoiceAnalysis | None = None,
        progress: Callable[[str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
        license_entitlement_id: str | None = None,
    ) -> CustomVoiceModel:
        def stage(name: str) -> None:
            if progress:
                progress(name)

        if not consent_given:
            raise CloneOrchestrationError(
                "CONSENT_REQUIRED", "Consent is required to create a voice profile."
            )
        if not display_name.strip():
            raise CloneOrchestrationError("INVALID_NAME", "Voice name is required.")

        audio_src = source_audio_path or reference_audio_path
        if audio_src is None:
            raise CloneOrchestrationError("INVALID_REFERENCE", "Reference audio path is required.")

        async with _clone_lock:
            stage("validating")
            duplicate = await session.scalar(
                select(CustomVoiceModel).where(
                    CustomVoiceModel.display_name == display_name.strip(),
                    CustomVoiceModel.status.in_(["creating", "ready"]),
                )
            )
            if duplicate:
                raise CloneOrchestrationError(
                    "DUPLICATE_NAME", "A voice with this name already exists."
                )
            if is_cancelled and is_cancelled():
                raise CloneOrchestrationError("CANCELLED", "Voice profile creation was cancelled.")

            voice_id = str(uuid.uuid4())
            profile_dir = settings.custom_voices_dir / voice_id
            profile_dir.mkdir(parents=True, exist_ok=True)

            stored_reference_duration = reference_duration_seconds or duration_seconds
            voice = CustomVoiceModel(
                id=voice_id,
                display_name=display_name.strip(),
                reference_audio_path=str(profile_dir / "reference.wav"),
                transcript=transcript.strip() or "[reference audio]",
                consent_given=True,
                consent_version="voice-lab-v1",
                provider_id="vieneu",
                engine_id="v3turbo",
                status="creating",
                profile_format_version="vieneu-enrollment-v2",
                denoise_mode=denoise_mode,
                clone_mode=clone_mode,
                duration_seconds=stored_reference_duration,
                source_duration_seconds=source_duration_seconds or duration_seconds,
                reference_duration_seconds=stored_reference_duration,
                selected_start_seconds=selected_start_seconds,
                selected_end_seconds=selected_end_seconds or stored_reference_duration,
                quality_score=quality_score,
                analysis_warnings=json.dumps(warnings or []),
                license_entitlement_id=license_entitlement_id,
            )
            stage("creating")
            session.add(voice)
            try:
                await session.commit()
                await session.refresh(voice)
            except Exception as exc:
                await session.rollback()
                raise CloneOrchestrationError(
                    "DATABASE_ERROR", "Voice profile could not be initialized."
                ) from exc

            async def mark_failed() -> None:
                voice.status = "failed"
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()

            engine = None
            try:
                engine = await self.manager.get_engine()
            except Exception as exc:
                logger.warning("Could not obtain shared engine: %s", exc)

            # 1. Canonical Reference Extraction & Preflight & Conditional Denoise
            stage("preparing_reference")
            if self._preflight is not None:
                try:
                    res = self._preflight(audio_src)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as exc:
                    await mark_failed()
                    raise CloneOrchestrationError(
                        getattr(exc, "code", "CLONE_PREFLIGHT_FAILED"),
                        getattr(exc, "message", str(exc)),
                    ) from exc

            try:
                proc_res = await process_voice_reference(
                    source_path=audio_src,
                    target_dir=profile_dir,
                    start_seconds=selected_start_seconds,
                    end_seconds=selected_end_seconds,
                    total_duration=source_duration_seconds or duration_seconds,
                    denoise_mode=denoise_mode,
                    analysis=analysis,
                    engine=engine,
                )
            except Exception as exc:
                await mark_failed()
                raise CloneOrchestrationError(
                    "REFERENCE_FAILED", f"Failed processing reference audio: {exc}"
                ) from exc

            if is_cancelled and is_cancelled():
                await mark_failed()
                raise CloneOrchestrationError("CANCELLED", "Voice profile creation was cancelled.")

            # 2. True Enrollment: Tensor extraction & NPZ persistence
            stage("enrolling")
            enrollment_service = VieneuEnrollmentService(model_manager=self.manager)
            active_ref = (
                proc_res.cleaned_reference_path
                if (proc_res.cleaned_reference_path and proc_res.denoise_applied)
                else proc_res.canonical_reference_path
            )

            try:
                enroll_res = await enrollment_service.enroll(
                    reference_audio_path=active_ref,
                    target_dir=profile_dir,
                    fingerprint=proc_res.fingerprint,
                    duration_seconds=proc_res.duration_seconds,
                    denoise_mode=denoise_mode,
                    denoise_applied=proc_res.denoise_applied,
                    clone_mode=clone_mode,
                )
            except Exception as exc:
                await mark_failed()
                raise CloneOrchestrationError(
                    "ENROLLMENT_FAILED", f"Failed enrolling voice reference: {exc}"
                ) from exc

            if is_cancelled and is_cancelled():
                await mark_failed()
                raise CloneOrchestrationError("CANCELLED", "Voice profile creation was cancelled.")

            # 3. Calibration synthesis & Speaker similarity
            stage("calibrating")
            calib_path = None
            similarity_score = None
            calib_quality = None
            if engine is not None:
                try:
                    calib_path, similarity_score, calib_quality = await synthesize_calibration(
                        engine=engine,
                        semaphore=enrollment_service.semaphore,
                        speaker_emb=enroll_res.speaker_emb,
                        ref_codes=enroll_res.ref_codes,
                        target_dir=profile_dir,
                        clone_mode=clone_mode,
                    )
                except Exception as exc:
                    logger.warning("Calibration synthesis failed: %s", exc)

            if is_cancelled and is_cancelled():
                await mark_failed()
                raise CloneOrchestrationError("CANCELLED", "Voice profile creation was cancelled.")

            # 4. Finalize and save
            stage("saving")
            voice.reference_audio_path = str(proc_res.canonical_reference_path)
            voice.enrollment_artifact_path = str(enroll_res.artifact_path)
            voice.cleaned_reference_audio_path = (
                str(proc_res.cleaned_reference_path) if proc_res.cleaned_reference_path else None
            )
            voice.calibration_audio_path = str(calib_path) if calib_path else None
            voice.engine_version = enroll_res.engine_version
            voice.reference_fingerprint = enroll_res.reference_fingerprint
            voice.denoise_applied = proc_res.denoise_applied
            voice.speaker_similarity_score = similarity_score
            voice.calibration_quality_score = calib_quality
            voice.enrollment_created_at = utc_now()
            voice.status = "ready"

            try:
                await session.commit()
                await session.refresh(voice)
            except Exception as exc:
                await session.rollback()
                raise CloneOrchestrationError(
                    "DATABASE_ERROR", "Voice profile could not be saved."
                ) from exc

            stage("ready")
            return voice
