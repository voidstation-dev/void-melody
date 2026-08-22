import asyncio
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


@pytest.mark.asyncio
async def test_clone_preflight_allows_cold_vieneu_runtime_warmup(monkeypatch, tmp_path: Path):
    from app.config import settings
    from app.services.clone_preflight import preflight_clone_reference
    from app.workers.queue_manager import queue_manager

    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"reference")
    provider = queue_manager.provider_registry["vieneu"]

    async def slow_first_enrollment(_path: Path) -> None:
        await asyncio.sleep(0.03)

    monkeypatch.setattr(provider, "preflight_clone_reference", slow_first_enrollment)
    monkeypatch.setattr(settings, "tts_provider_timeout_seconds", 0.01)
    monkeypatch.setattr(settings, "vieneu_clone_timeout_seconds", 0.1)

    await preflight_clone_reference(reference_path)
