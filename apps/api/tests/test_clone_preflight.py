from pathlib import Path

import pytest

from app.services.clone_orchestrator import CloneOrchestrator


@pytest.mark.asyncio
async def test_clone_orchestrator_runs_enrollment_preflight_before_persisting(
    async_session, monkeypatch, tmp_path: Path
):
    preflight_paths: list[Path] = []

    async def fake_preflight(path: Path) -> None:
        preflight_paths.append(path)

    monkeypatch.setattr(
        "app.services.clone_orchestrator.create_reference_profile",
        lambda *args, **kwargs: None,
    )
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"reference")

    voice = await CloneOrchestrator(preflight=fake_preflight).create(
        session=async_session,
        display_name="Preflighted voice",
        transcript="hello",
        consent_given=True,
        reference_audio_path=reference_path,
        duration_seconds=4.0,
    )

    assert preflight_paths == [reference_path]
    assert voice.status == "ready"
