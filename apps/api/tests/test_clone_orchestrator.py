from pathlib import Path

import pytest

from app.services.clone_orchestrator import CloneOrchestrator
from app.services.clone_preflight import ClonePreflightError
from app.models.custom_voice import CustomVoiceModel
from sqlalchemy import select


@pytest.mark.asyncio
async def test_clone_orchestrator_serializes_and_saves_reference_profile(async_session, tmp_path: Path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")
    stages: list[str] = []

    async def fake_preflight(_path: Path) -> None:
        return None

    voice = await CloneOrchestrator(preflight=fake_preflight).create(
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
    assert stages == ["validating", "creating", "preparing_reference", "saving", "ready"]


@pytest.mark.asyncio
async def test_clone_orchestrator_marks_failed_profile_after_preflight_failure(
    async_session, tmp_path: Path
):
    reference = tmp_path / "failed-reference.wav"
    reference.write_bytes(b"reference")

    async def failing_preflight(_path: Path) -> None:
        raise ClonePreflightError("CLONE_PREFLIGHT_FAILED", "enrollment failed")

    with pytest.raises(ValueError, match="enrollment failed"):
        await CloneOrchestrator(preflight=failing_preflight).create(
            session=async_session,
            display_name="Failed voice",
            transcript="hello",
            consent_given=True,
            reference_audio_path=reference,
            duration_seconds=4.0,
        )

    failed = await async_session.scalar(
        select(CustomVoiceModel).where(CustomVoiceModel.display_name == "Failed voice")
    )
    assert failed is not None
    assert failed.status == "failed"


@pytest.mark.asyncio
async def test_clone_orchestrator_requires_consent(async_session, tmp_path: Path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"reference")

    with pytest.raises(ValueError, match="Consent"):
        await CloneOrchestrator(preflight=lambda _path: None).create(
            session=async_session,
            display_name="No consent",
            transcript="Xin chào",
            consent_given=False,
            reference_audio_path=reference,
            duration_seconds=4.0,
        )
