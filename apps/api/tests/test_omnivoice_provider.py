"""Tests for OmniVoiceProvider end-to-end synthesis path."""

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.models.tts_job import TTSJobModel
from app.providers.omnivoice_provider import OmniVoiceProvider
from app.services.omnivoice_model_service import OmniVoiceModelService
from app.services.omnivoice_runtime import OmniVoiceRuntimeClient
from app.services.omnivoice_voice_resolver import OmniVoiceResolutionError
from app.services.tts_service import create_tts_job
from app.utils.audio_utils import get_audio_duration
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
def installed_model_dir(tmp_path: Path, monkeypatch):
    """Create a fake installed G-OmniVoice model snapshot and patch the singleton."""
    model_dir = tmp_path / "models" / "omnivoice" / "g-omnivoice" / "2025-08-20-a"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}")
    (model_dir / "model.safetensors").write_text("weights")
    tokenizer_dir = model_dir / "tokenizer"
    tokenizer_dir.mkdir()
    (tokenizer_dir / "vocab.json").write_text("[]")

    svc = OmniVoiceModelService(model_dir=model_dir)
    monkeypatch.setattr(
        "app.providers.omnivoice_provider.omnivoice_model_service",
        svc,
    )
    return model_dir


@pytest.fixture
def patch_db(async_session_factory, monkeypatch):
    """Route all AsyncSessionLocal consumers to the test database."""
    monkeypatch.setattr(
        "app.providers.omnivoice_provider.AsyncSessionLocal",
        async_session_factory,
    )
    monkeypatch.setattr(
        "app.database.AsyncSessionLocal",
        async_session_factory,
    )
    return async_session_factory


@pytest_asyncio.fixture
async def saved_omnivoice_voice(
    async_session_factory,
    installed_model_dir,
    patch_db,
    tmp_path: Path,
):
    """Persist a ready OmniVoice voice with a valid VoiceClonePrompt artifact."""
    prompt_path = tmp_path / "voices" / "omnivoice" / "voice-1" / "voice-prompt.bin"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_bytes(b"OMNIVOICE_VOICE_CLONE_PROMPT_V1")

    voice = OmniVoiceVoiceModel(
        id="voice-1",
        display_name="Luna",
        provider_id="omnivoice",
        engine_id="g-omnivoice",
        voice_kind="design",
        status="ready",
        design_prompt="A warm Vietnamese female storyteller",
        compiled_instruction="Warm Vietnamese female storyteller",
        preview_text="Xin chào, đây là giọng nói mẫu.",
        selected_preview_audio_path=str(
            tmp_path / "voices" / "omnivoice" / "voice-1" / "source-preview.wav"
        ),
        prompt_artifact_path=str(prompt_path),
        prompt_format_version="omnivoice-voice-clone-prompt",
        model_id="g-omnivoice",
        model_revision="2025-08-20-a",
        engine_version="0.2.1",
        sample_rate=24000,
        voice_revision="v1",
    )

    async with async_session_factory() as session:
        session.add(voice)
        await session.commit()
    return voice


@pytest.mark.asyncio
async def test_omnivoice_provider_synthesizes_wav(
    saved_omnivoice_voice,
    tmp_path: Path,
    monkeypatch,
):
    """Provider directly synthesizes a WAV file from a saved VoiceClonePrompt."""
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)

    runtime = OmniVoiceRuntimeClient(mock_mode=True)
    provider = OmniVoiceProvider(runtime_client=runtime)

    destination = tmp_path / "audio" / "out.wav"
    result = await provider.synthesize(
        text="Xin chào.",
        voice_type=saved_omnivoice_voice.id,
        destination_path=destination,
    )

    assert result.mime_type == "audio/wav"
    assert result.sample_rate == 24000
    assert result.local_paths
    assert Path(result.local_paths[0]).is_file()
    assert Path(result.local_paths[0]).stat().st_size > 0


@pytest.mark.asyncio
async def test_omnivoice_provider_list_voices(
    saved_omnivoice_voice,
):
    provider = OmniVoiceProvider()
    voices = await provider.list_voices(language="vi-VN")

    ids = {v.voice_type for v in voices}
    assert saved_omnivoice_voice.id in ids
    assert all(v.provider_id == "omnivoice" for v in voices)


@pytest.mark.asyncio
async def test_omnivoice_provider_missing_voice_raises(
    installed_model_dir,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)

    provider = OmniVoiceProvider()
    with pytest.raises(OmniVoiceResolutionError) as exc_info:
        await provider.synthesize(text="Hi", voice_type="does-not-exist")
    assert exc_info.value.code == "VOICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_tts_worker_omnivoice_job_end_to_end(
    async_session_factory,
    saved_omnivoice_voice,
    tmp_path: Path,
    monkeypatch,
):
    """A full Audio Studio-style TTS job with provider_id=omnivoice completes."""
    monkeypatch.setattr("app.workers.tts_worker.AsyncSessionLocal", async_session_factory)
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "tts_apply_rate_with_ffmpeg", False)

    async with async_session_factory() as session:
        job = await create_tts_job(
            session,
            text="Xin chào thế giới.",
            voice_type=saved_omnivoice_voice.id,
            voice_display_name="Luna",
            language_code="vi-VN",
            provider_id="omnivoice",
            export_format="wav",
        )
        job_id = job.id

    provider_registry = {
        "omnivoice": OmniVoiceProvider(
            runtime_client=OmniVoiceRuntimeClient(mock_mode=True)
        ),
    }
    await execute_tts_job_step(
        job_id,
        provider_registry=provider_registry,
        worker_id=1,
    )

    async with async_session_factory() as session:
        reloaded = await session.get(TTSJobModel, job_id)
        assert reloaded is not None
        assert reloaded.status == "completed"
        assert reloaded.audio_path is not None
        assert Path(reloaded.audio_path).is_file()
        assert reloaded.audio_mime_type == "audio/wav"
        assert reloaded.audio_file_size is not None
        assert reloaded.audio_duration is not None
