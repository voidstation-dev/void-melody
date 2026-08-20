from pathlib import Path

import pytest

from vieneu_core.voice_profiles import (
    VoiceProfileRequest,
    VoiceProfileValidationError,
    create_reference_profile,
)


def test_reference_profile_is_portable_and_reports_progress(tmp_path: Path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"wav")
    progress: list[str] = []

    result = create_reference_profile(
        VoiceProfileRequest(
            profile_id="voice-1",
            reference_audio_path=reference,
            transcript="Xin chào",
        ),
        progress=progress.append,
    )

    assert result.profile_id == "voice-1"
    assert result.strategy == "reference-backed"
    assert result.reference_audio_path == reference
    assert progress == ["validating", "ready"]


def test_reference_profile_rejects_missing_audio(tmp_path: Path):
    with pytest.raises(VoiceProfileValidationError) as error:
        create_reference_profile(
            VoiceProfileRequest(
                profile_id="voice-1",
                reference_audio_path=tmp_path / "missing.wav",
                transcript="Xin chào",
            )
        )

    assert error.value.code == "INVALID_REFERENCE"


def test_reference_profile_honors_cancellation(tmp_path: Path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"wav")

    with pytest.raises(VoiceProfileValidationError) as error:
        create_reference_profile(
            VoiceProfileRequest(profile_id="voice-1", reference_audio_path=reference),
            is_cancelled=lambda: True,
        )

    assert error.value.code == "CANCELLED"
