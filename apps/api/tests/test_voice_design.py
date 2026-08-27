"""Tests for Voice Design orchestration: previews and commit/freeze."""

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.services.omnivoice_model_service import OmniVoiceModelService
from app.services.omnivoice_runtime import OmniVoiceRuntimeClient
from app.services.voice_design import VoiceDesignOrchestrator
from app.services.voice_design.orchestrator import VoiceDesignError
from app.services.voice_design.preview_store import (
    delete_session,
    get_candidate_audio_path,
    load_session,
)


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
    model_dir = tmp_path / "models" / "omnivoice" / "g-omnivoice" / "2025-08-20-a"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}")
    (model_dir / "model.safetensors").write_text("weights")
    tokenizer_dir = model_dir / "tokenizer"
    tokenizer_dir.mkdir()
    (tokenizer_dir / "vocab.json").write_text("[]")

    svc = OmniVoiceModelService(model_dir=model_dir)
    monkeypatch.setattr(
        "app.services.voice_design.orchestrator.omnivoice_model_service",
        svc,
    )
    monkeypatch.setattr(
        "app.providers.omnivoice_provider.omnivoice_model_service",
        svc,
    )
    monkeypatch.setattr(
        "app.database.AsyncSessionLocal",
        None,
    )
    return model_dir


@pytest.fixture
def patch_db(async_session_factory, monkeypatch):
    monkeypatch.setattr(
        "app.providers.omnivoice_provider.AsyncSessionLocal",
        async_session_factory,
    )
    monkeypatch.setattr(
        "app.database.AsyncSessionLocal",
        async_session_factory,
    )
    return async_session_factory


@pytest.fixture
def orchestrator(installed_model_dir, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "custom_voices_dir", tmp_path / "voices")
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "voices").mkdir(parents=True, exist_ok=True)

    runtime = OmniVoiceRuntimeClient(mock_mode=True)
    return VoiceDesignOrchestrator(runtime_client=runtime)


@pytest.mark.asyncio
async def test_voice_design_generates_previews(
    orchestrator,
    patch_db,
):
    result = await orchestrator.generate_previews(
        prompt="A warm Vietnamese female storyteller",
        language="vi",
        preview_text="Xin chào thế giới.",
        count=3,
        attributes={"gender": "female", "age": "young-adult", "style": "storytelling"},
    )

    assert result.session_id
    assert "warm" in result.compiled_instruction.lower() or "storytelling" in result.compiled_instruction.lower()
    assert len(result.candidates) == 3

    session = load_session(result.session_id)
    assert session is not None
    assert session.status == "active"
    assert len(session.candidates) == 3
    for c in session.candidates:
        assert c.audio_path.is_file()
        assert c.audio_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_voice_design_commit_freezes_voice(
    orchestrator,
    async_session_factory,
    patch_db,
):
    preview_result = await orchestrator.generate_previews(
        prompt="A warm Vietnamese female storyteller",
        language="vi",
        preview_text="Xin chào thế giới.",
        count=2,
    )

    selected = preview_result.candidates[0]
    async with async_session_factory() as session:
        commit = await orchestrator.commit_voice(
            session_id=preview_result.session_id,
            candidate_id=selected["id"],
            display_name="Luna",
            session=session,
        )

    assert commit.voice_id
    assert commit.display_name == "Luna"
    assert commit.provider_id == "omnivoice"
    assert commit.voice_kind == "design"
    assert commit.status == "ready"

    # Session marked committed and voice persisted
    session_state = load_session(preview_result.session_id)
    assert session_state is not None
    assert session_state.status == "committed"
    async with async_session_factory() as session:
        voice = await session.get(OmniVoiceVoiceModel, commit.voice_id)
        assert voice is not None
        assert voice.prompt_artifact_path is not None
        assert Path(voice.prompt_artifact_path).is_file()
        assert voice.compiled_instruction is not None


@pytest.mark.asyncio
async def test_voice_design_commit_rejects_missing_candidate(
    orchestrator,
    async_session_factory,
    patch_db,
):
    preview_result = await orchestrator.generate_previews(
        prompt="A warm Vietnamese female storyteller",
        count=1,
    )

    async with async_session_factory() as session:
        with pytest.raises(VoiceDesignError) as exc_info:
            await orchestrator.commit_voice(
                session_id=preview_result.session_id,
                candidate_id="not-real",
                display_name="Luna",
                session=session,
            )
        assert exc_info.value.code == "VOICE_DESIGN_CANDIDATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_voice_design_commit_rejects_committed_session(
    orchestrator,
    async_session_factory,
    patch_db,
):
    preview_result = await orchestrator.generate_previews(
        prompt="A warm Vietnamese female storyteller",
        count=1,
    )

    selected = preview_result.candidates[0]
    async with async_session_factory() as session:
        await orchestrator.commit_voice(
            session_id=preview_result.session_id,
            candidate_id=selected["id"],
            display_name="Luna",
            session=session,
        )

    async with async_session_factory() as session:
        with pytest.raises(VoiceDesignError) as exc_info:
            await orchestrator.commit_voice(
                session_id=preview_result.session_id,
                candidate_id=selected["id"],
                display_name="Luna 2",
                session=session,
            )
        assert exc_info.value.code == "VOICE_DESIGN_SESSION_EXPIRED"
