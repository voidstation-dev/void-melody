"""Portable, reference-backed voice profile domain.

Profiles intentionally reference a normalized local audio artifact instead of
serializing engine tensors. This keeps the first Voice Lab strategy stable
across process restarts and CPU/ CUDA packaging variants.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class VoiceProfileValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class VoiceProfileRequest:
    profile_id: str
    reference_audio_path: Path
    transcript: str | None = None
    denoise: bool = True


@dataclass(frozen=True)
class VoiceProfileResult:
    profile_id: str
    reference_audio_path: Path
    strategy: str
    engine_id: str = "v3turbo"
    format_version: str = "reference-v1"


@dataclass(frozen=True)
class EnrolledVoiceProfileResult:
    profile_id: str
    reference_audio_path: Path
    enrollment_artifact_path: Path
    strategy: str = "enrolled"
    engine_id: str = "v3turbo"
    format_version: str = "vieneu-enrollment-v2"
    cleaned_reference_audio_path: Path | None = None
    calibration_audio_path: Path | None = None
    engine_version: str | None = None
    reference_fingerprint: str | None = None
    denoise_mode: str = "auto"
    denoise_applied: bool | None = None
    clone_mode: str = "fidelity"
    speaker_similarity_score: float | None = None
    calibration_quality_score: int | None = None


def create_reference_profile(
    request: VoiceProfileRequest,
    *,
    progress: Callable[[str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> VoiceProfileResult:
    """Validate a reference-backed profile without loading the ML engine."""

    def report(stage: str) -> None:
        if progress:
            progress(stage)

    if is_cancelled and is_cancelled():
        raise VoiceProfileValidationError("CANCELLED", "Voice profile creation was cancelled.")
    report("validating")
    path = request.reference_audio_path
    if not request.profile_id.strip():
        raise VoiceProfileValidationError("INVALID_PROFILE", "Profile id is required.")
    if not path.is_file() or path.stat().st_size == 0:
        raise VoiceProfileValidationError("INVALID_REFERENCE", "Reference audio is missing or empty.")
    if request.transcript is not None and not request.transcript.strip():
        raise VoiceProfileValidationError("INVALID_TRANSCRIPT", "Transcript cannot be empty.")
    if is_cancelled and is_cancelled():
        raise VoiceProfileValidationError("CANCELLED", "Voice profile creation was cancelled.")
    report("ready")
    return VoiceProfileResult(profile_id=request.profile_id, reference_audio_path=path, strategy="reference-backed")
