from pathlib import Path

import pytest

from app.services.clone_orchestrator import CloneOrchestrator


@pytest.mark.asyncio
async def test_clone_orchestrator_serializes_and_saves_reference_profile(async_session, tmp_path: Path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")
    stages: list[str] = []

    voice = await CloneOrchestrator().create(
        session=async_session,
        display_name="Orchestrated voice",
        transcript="Xin chào",
        consent_given=True,
        reference_audio_path=reference,
        duration_seconds=4.0,
        progress=stages.append,
    )

    assert voice.status == "ready"
    assert voice.reference_audio_path == str(reference)
    assert stages == ["validating", "preparing_reference", "saving", "ready"]


@pytest.mark.asyncio
async def test_clone_orchestrator_requires_consent(async_session, tmp_path: Path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")

    with pytest.raises(ValueError, match="Consent"):
        await CloneOrchestrator().create(
            session=async_session,
            display_name="No consent",
            transcript="Xin chào",
            consent_given=False,
            reference_audio_path=reference,
            duration_seconds=4.0,
        )
