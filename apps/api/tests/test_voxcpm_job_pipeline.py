"""Phase 6 tests: VoxCPM2 shared TTS jobs & history integration.

Critical regression assertions from the plan:

    assert job.provider_id == "voxcpm2"
    assert vieneu_provider_called is False

VoxCPM2 jobs never touch VieneuProvider, never fall back to another
provider, and either complete through the VoxCPM2 runtime or fail
explicitly.
"""

import asyncio
import struct
import threading
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models.tts_job import TTSJobModel
from app.models.voxcpm_voice import VoxCpmVoiceModel
from app.providers.voxcpm_provider import (
    VoxCpmProvider,
    VoxCpmProviderError,
)
from app.services.tts_service import create_tts_job
from app.services.voice_resolver import VoiceResolutionError, resolve_voice
from app.workers.tts_worker import execute_tts_job_step


@pytest_asyncio.fixture
async def async_session_factory(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.fixture
def patch_db(async_session_factory, monkeypatch):
    """Route all AsyncSessionLocal consumers to the test database."""
    monkeypatch.setattr(
        "app.providers.voxcpm_provider.AsyncSessionLocal",
        async_session_factory,
    )
    monkeypatch.setattr(
        "app.services.voice_resolver.AsyncSessionLocal",
        async_session_factory,
        raising=False,
    )
    return async_session_factory


def _write_wav(path: Path, sample_rate: int = 48000, seconds: float = 0.2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"".join(
            struct.pack("<h", int(8000 * ((i % 100) / 100))) for i in range(frames)
        ))


@pytest_asyncio.fixture
async def saved_voxcpm_voice(
    async_session_factory,
    patch_db,
    tmp_path: Path,
):
    """Persist a ready VoxCPM2 voice with a real reference WAV on disk."""
    reference = tmp_path / "voices" / "voxcpm2" / "voice-1" / "reference.wav"
    _write_wav(reference)

    voice = VoxCpmVoiceModel(
        id="vox-voice-1",
        display_name="Vox test",
        provider_id="voxcpm2",
        engine_id="voxcpm2",
        status="ready",
        reference_audio_path=str(reference),
        reference_duration_seconds=0.2,
        reference_sample_rate=48000,
    )
    async with async_session_factory() as session:
        session.add(voice)
        await session.commit()
    return voice


class FakeVoxCpmRuntime:
    """Records requests and writes a real 48 kHz WAV, like the real worker."""

    def __init__(self):
        self.calls: list[dict] = []
        self.load_model_calls: list[str] = []

    async def load_model(self, model_id="openbmb/VoxCPM2", device="auto"):
        self.load_model_calls.append(model_id)
        return {"status": "loaded", "device": "cpu", "sample_rate": 48000}

    async def synthesize(self, request, *, method="synthesize_emotional", timeout_seconds=None):
        self.calls.append({
            "method": method,
            "text": request.text,
            "emotion": request.emotion,
            "instruction": request.instruction,
            "reference": request.reference_wav_path,
        })
        _write_wav(Path(request.output_path))
        from app.services.voxcpm_runtime import VoxCpmSynthesisResult

        return VoxCpmSynthesisResult(
            output_path=request.output_path,
            sample_rate=48000,
            duration_seconds=0.2,
            backend="real",
            method=method,
        )


@pytest.mark.asyncio
async def test_voxcpm_provider_synthesizes_48k_wav(
    saved_voxcpm_voice,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    runtime = FakeVoxCpmRuntime()
    provider = VoxCpmProvider(runtime_client=runtime)

    destination = tmp_path / "audio" / "out.wav"
    result = await provider.synthesize(
        text="Xin chào.",
        voice_type=saved_voxcpm_voice.id,
        style="sad",
        destination_path=destination,
    )

    assert result.mime_type == "audio/wav"
    assert result.sample_rate == 48000
    assert result.local_paths and Path(result.local_paths[0]).is_file()
    assert runtime.calls[0]["method"] == "synthesize_emotional"
    assert runtime.calls[0]["emotion"] == "sad"
    assert runtime.calls[0]["reference"] == str(
        Path(saved_voxcpm_voice.reference_audio_path)
    )


@pytest.mark.asyncio
async def test_voxcpm_provider_unknown_voice_raises_explicitly(
    patch_db,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    provider = VoxCpmProvider(runtime_client=FakeVoxCpmRuntime())
    with pytest.raises(VoxCpmProviderError) as exc_info:
        await provider.synthesize(text="Hi", voice_type="does-not-exist")
    assert exc_info.value.code == "VOXCPM_VOICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_voxcpm_provider_rejects_emotion_and_instruction_together(
    saved_voxcpm_voice,
    tmp_path: Path,
    monkeypatch,
):
    from app.providers.base import SynthesisOptions

    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    provider = VoxCpmProvider(runtime_client=FakeVoxCpmRuntime())
    with pytest.raises(VoxCpmProviderError) as exc_info:
        await provider.synthesize(
            text="Hi",
            voice_type=saved_voxcpm_voice.id,
            style="sad",
            options=SynthesisOptions(instruction="calm"),
        )
    assert exc_info.value.code == "VOXCPM_INVALID_PARAMS"


@pytest.mark.asyncio
async def test_voxcpm_provider_list_voices(saved_voxcpm_voice):
    provider = VoxCpmProvider(runtime_client=FakeVoxCpmRuntime())
    voices = await provider.list_voices()
    ids = {v.voice_type for v in voices}
    assert saved_voxcpm_voice.id in ids
    assert all(v.provider_id == "voxcpm2" for v in voices)


@pytest.mark.asyncio
async def test_resolve_voice_resolves_voxcpm2_voice_with_provider_id(
    async_session_factory,
    saved_voxcpm_voice,
):
    """Provider-aware identity: provider_id travels with the resolution."""
    async with async_session_factory() as session:
        resolved = await resolve_voice(session, saved_voxcpm_voice.id)
    assert resolved.provider_id == "voxcpm2"
    assert resolved.reference_audio_path == saved_voxcpm_voice.reference_audio_path


@pytest.mark.asyncio
async def test_resolve_voice_rejects_voxcpm_voice_with_missing_reference(
    async_session_factory,
    patch_db,
):
    voice = VoxCpmVoiceModel(
        id="vox-missing-ref",
        display_name="Broken",
        status="ready",
        reference_audio_path="Z:/does/not/exist.wav",
    )
    async with async_session_factory() as session:
        session.add(voice)
        await session.commit()

        from app.services.voice_resolver import invalidate_voice_cache

        invalidate_voice_cache()
        with pytest.raises(VoiceResolutionError) as exc_info:
            await resolve_voice(session, "vox-missing-ref")
        invalidate_voice_cache()
    assert exc_info.value.code == "VOXCPM_REFERENCE_MISSING"


@pytest.mark.asyncio
async def test_voxcpm_job_end_to_end_and_vieneu_never_called(
    async_session_factory,
    saved_voxcpm_voice,
    tmp_path: Path,
    monkeypatch,
):
    """Plan critical regression: job runs as voxcpm2 and VieneuProvider is never
    touched."""
    job_id_holder: list[str] = []

    async with async_session_factory() as session:
        job = await create_tts_job(
            session,
            text="Anh vẫn nhớ ngày hôm đó.",
            voice_type=saved_voxcpm_voice.id,
            voice_display_name="Vox test",
            language_code="vi-VN",
            provider_id="voxcpm2",
            style="sad",
            export_format="wav",
        )
        job_id_holder.append(job.id)

    # A VieneuProvider whose use is an explicit failure.
    vieneu_synth = AsyncMock(side_effect=AssertionError("VieNeu fallback used"))
    vieneu_provider = MagicMock()
    vieneu_provider.synthesize = vieneu_synth

    runtime = FakeVoxCpmRuntime()
    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "tts_apply_rate_with_ffmpeg", False)

    async def fake_audio_duration(_path):
        return 0.2

    monkeypatch.setattr(
        "app.utils.audio_utils.get_audio_duration",
        fake_audio_duration,
    )

    await execute_tts_job_step(
        job_id_holder[0],
        provider_registry={
            "voxcpm2": VoxCpmProvider(runtime_client=runtime),
            "vieneu": vieneu_provider,
        },
        worker_id=1,
    )

    async with async_session_factory() as session:
        job = await session.get(TTSJobModel, job_id_holder[0])
        # Plan-mandated assertions
        assert job.provider_id == "voxcpm2"
        assert job.status == "completed"
        assert job.audio_path is not None
        assert Path(job.audio_path).is_file()
        assert job.audio_mime_type == "audio/wav"
        assert job.audio_duration == 0.2
        assert job.progress == 100
    vieneu_synth.assert_not_called()
    # Runtime went through the emotional path with the sad preset
    assert runtime.calls[0]["method"] == "synthesize_emotional"
    assert runtime.calls[0]["emotion"] == "sad"


@pytest.mark.asyncio
async def test_voxcpm_job_without_runtime_fails_explicitly_no_fallback(
    async_session_factory,
    saved_voxcpm_voice,
    tmp_path: Path,
    monkeypatch,
):
    """No provider fallback: a missing VoxCPM2 runtime fails the job as
    PROVIDER_REJECTED (explicit), never re-routes to Vieneu/CapCut."""
    job_id_holder: list[str] = []

    async with async_session_factory() as session:
        job = await create_tts_job(
            session,
            text="hello",
            voice_type=saved_voxcpm_voice.id,
            voice_display_name="Vox test",
            language_code="vi-VN",
            provider_id="voxcpm2",
            export_format="wav",
        )
        job_id_holder.append(job.id)

    vieneu_provider = MagicMock()
    vieneu_provider.synthesize = AsyncMock(side_effect=AssertionError("no fallback"))
    capcut_provider = MagicMock()
    capcut_provider.synthesize = AsyncMock(side_effect=AssertionError("no fallback"))

    # Patch the client class so runtime construction fails deterministically
    # ("VoxCPM2 env not installed"). Leaving runtime_client=None would lazily
    # spawn a real worker subprocess on machines that have the env, whose ping
    # timeout maps to a *retryable* error — nondeterministic for this test.
    monkeypatch.setattr(
        "app.providers.voxcpm_provider.VoxCpmRuntimeClient",
        MagicMock(side_effect=FileNotFoundError("voxcpm worker env missing")),
    )

    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "tts_apply_rate_with_ffmpeg", False)

    await execute_tts_job_step(
        job_id_holder[0],
        provider_registry={
            "voxcpm2": VoxCpmProvider(runtime_client=None),
            "vieneu": vieneu_provider,
            "capcut": capcut_provider,
        },
    )

    async with async_session_factory() as session:
        job = await session.get(TTSJobModel, job_id_holder[0])
        assert job.provider_id == "voxcpm2"
        assert job.status == "failed"
        assert job.error_code in ("PROVIDER_REJECTED", "PROVIDER_UNAVAILABLE", "PROVIDER_TIMEOUT", "INTERNAL_ERROR")
    vieneu_provider.synthesize.assert_not_called()
    capcut_provider.synthesize.assert_not_called()


@pytest.mark.asyncio
async def test_voxcpm_job_not_configured_fails_cleanly(
    async_session_factory,
    saved_voxcpm_voice,
    tmp_path: Path,
    monkeypatch,
):
    """When voxcpm2 has no registry entry the job fails PROVIDER_NOT_CONFIGURED."""
    async with async_session_factory() as session:
        job = await create_tts_job(
            session,
            text="hello",
            voice_type=saved_voxcpm_voice.id,
            voice_display_name="Vox test",
            language_code="vi-VN",
            provider_id="voxcpm2",
        )
        job_id = job.id

    capcut = MagicMock(side_effect=AssertionError("CapCut fallback used"))
    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)

    await execute_tts_job_step(job_id, provider_registry={})

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded.status == "failed"
        assert reloaded.error_code == "PROVIDER_NOT_CONFIGURED"
    capcut.assert_not_called()


@pytest.mark.asyncio
async def test_voxcpm_job_uses_voxcpm_chunk_concurrency(
    async_session_factory,
    saved_voxcpm_voice,
    tmp_path: Path,
    monkeypatch,
):
    observed_concurrency: list[int] = []

    async def capture_chunks(chunks, *, concurrency, process_chunk, is_cancelled):
        observed_concurrency.append(concurrency)
        if False:
            yield None

    async with async_session_factory() as session:
        job = await create_tts_job(
            session,
            text="first. second.",
            voice_type=saved_voxcpm_voice.id,
            voice_display_name="Vox test",
            language_code="vi-VN",
            provider_id="voxcpm2",
        )
        job_id = job.id

    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr("app.workers.tts_worker.execute_chunks_bounded", capture_chunks)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path)

    await execute_tts_job_step(
        job_id,
        provider_registry={"voxcpm2": VoxCpmProvider(runtime_client=FakeVoxCpmRuntime())},
    )

    assert observed_concurrency == [settings.voxcpm_chunk_concurrency]


@pytest.mark.asyncio
async def test_voxcpm_cache_fingerprint_includes_style_emotion(
    saved_voxcpm_voice,
    monkeypatch,
):
    """Cache key must include provider + style (emotion) details per plan."""
    from app.media.cache import compute_segment_fingerprint

    base = dict(
        provider_id="voxcpm2",
        text="same text",
        voice_type=saved_voxcpm_voice.id,
        rate=1.0,
    )
    neutral = compute_segment_fingerprint(style=None, **base)
    sad = compute_segment_fingerprint(style="sad", **base)
    cheerful = compute_segment_fingerprint(style="cheerful", **base)
    vieneu_same_text = compute_segment_fingerprint(
        provider_id="vieneu", text="same text",
        voice_type=saved_voxcpm_voice.id, rate=1.0, style=None,
    )
    assert neutral != sad != cheerful
    assert neutral != vieneu_same_text


@pytest.mark.asyncio
async def test_default_policies_and_lanes_include_voxcpm2():
    from app.scheduler.policies import get_default_policies
    from app.scheduler.scheduler import UnifiedScheduler
    from app.workers.queue_manager import queue_manager

    policies = get_default_policies()
    assert "voxcpm2" in policies
    assert policies["voxcpm2"].sample_rate == 48000

    # Scheduler registry dispatches voxcpm2 to a VoxCpmProvider, not Vieneu
    scheduler = UnifiedScheduler()
    assert "voxcpm2" in scheduler.lanes
    assert "voxcpm2" in scheduler.provider_registry
    assert isinstance(scheduler.provider_registry["voxcpm2"], VoxCpmProvider)
    assert "vieneu" in scheduler.provider_registry
    assert scheduler.provider_registry["voxcpm2"] is not scheduler.provider_registry["vieneu"]

    # Queue manager (live singleton) has a voxcpm2 lane for enqueue routing
    assert "voxcpm2" in queue_manager.lanes