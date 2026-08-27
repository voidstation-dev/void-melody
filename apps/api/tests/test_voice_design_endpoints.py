"""HTTP-level tests for Voice Design API and provider isolation."""

from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.voice_design import _get_orchestrator
from app.main import app
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.providers.registry import OMNIVOICE
from app.services.omnivoice_model_service import OmniVoiceModelService
from app.services.omnivoice_runtime import OmniVoiceRuntimeClient
from app.services.voice_design import VoiceDesignOrchestrator
from app.services.voice_design.preview_store import load_session
from tests.conftest import make_pro_entitlement


def _orchestrator_factory():
    return VoiceDesignOrchestrator(
        runtime_client=OmniVoiceRuntimeClient(mock_mode=True),
    )


app.dependency_overrides[_get_orchestrator] = _orchestrator_factory


@pytest.fixture(autouse=True)
def pro_entitlement(monkeypatch):
    """Make the auth middleware resolve every request to a synthetic pro entitlement."""

    async def fake_resolve_entitlement(_session, _license_key):
        return make_pro_entitlement()

    monkeypatch.setattr(
        "app.middleware.local_auth.resolve_entitlement",
        fake_resolve_entitlement,
    )


@pytest_asyncio.fixture
async def async_session_factory(tmp_path):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.database import Base

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
        "app.api.v1.voice_design.omnivoice_model_service",
        svc,
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
    monkeypatch.setattr(
        "app.api.v1.voice_design.get_async_session",
        lambda: async_session_factory(),
    )
    monkeypatch.setattr(
        "app.api.v1.voice_design._get_orchestrator",
        _orchestrator_factory,
    )
    return async_session_factory


@pytest.fixture
def patch_storage(tmp_path: Path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "audio_storage_dir", tmp_path / "audio")
    monkeypatch.setattr(settings, "custom_voices_dir", tmp_path / "voices")
    (tmp_path / "audio").mkdir(parents=True, exist_ok=True)
    (tmp_path / "voices").mkdir(parents=True, exist_ok=True)


@pytest.mark.asyncio
async def test_voice_design_capabilities_enabled(
    installed_model_dir,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tts/voice-design/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["providerId"] == "omnivoice"
    assert payload["supportsPromptDesign"] is True


@pytest.mark.asyncio
async def test_voice_design_capabilities_disabled_when_model_missing(
    monkeypatch,
):
    from app.services.omnivoice_model_service import OmniVoiceModelService

    monkeypatch.setattr(
        "app.api.v1.voice_design.omnivoice_model_service",
        OmniVoiceModelService(model_dir=Path("/nonexistent")),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tts/voice-design/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["reasonCode"] == "OMNI_MODEL_NOT_INSTALLED"


@pytest.mark.asyncio
async def test_voice_design_previews_and_commit_flow(
    installed_model_dir,
    patch_db,
    patch_storage,
    tmp_path: Path,
):
    from app.config import settings
    from app.services.omnivoice_runtime import OmniVoiceRuntimeClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        preview_resp = await client.post(
            "/api/v1/tts/voice-design/previews",
            json={
                "prompt": "A calm Vietnamese female narrator",
                "language": "vi-VN",
                "previewText": "Xin chào, đây là giọng nói mẫu.",
                "count": 2,
            },
        )

    assert preview_resp.status_code == 201
    preview = preview_resp.json()
    session_id = preview["sessionId"]
    assert len(preview["candidates"]) == 2
    candidate_id = preview["candidates"][0]["id"]

    # Candidate audio endpoint returns WAV
    audio_url = f"/api/v1/tts/voice-design/sessions/{session_id}/candidates/{candidate_id}/audio"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        audio_resp = await client.get(audio_url)
    assert audio_resp.status_code == 200
    assert audio_resp.headers["content-type"] == "audio/wav"
    assert len(audio_resp.content) > 0

    # Commit endpoint creates OmniVoice voice
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        commit_resp = await client.post(
            f"/api/v1/tts/voice-design/sessions/{session_id}/commit",
            json={"candidateId": candidate_id, "displayName": "Narrator A"},
        )

    assert commit_resp.status_code == 201
    commit = commit_resp.json()
    assert commit["providerId"] == "omnivoice"
    assert commit["voiceKind"] == "design"
    assert commit["status"] == "ready"

    # Session is committed
    session = load_session(session_id)
    assert session is not None
    assert session.status == "committed"

    # Voice persisted in database
    async with patch_db() as session:
        voice = await session.get(OmniVoiceVoiceModel, commit["voiceId"])
        assert voice is not None
        assert voice.provider_id == "omnivoice"
        assert Path(voice.prompt_artifact_path).is_file()


@pytest.mark.asyncio
async def test_voice_design_commit_rejects_unknown_candidate(
    installed_model_dir,
    patch_db,
    patch_storage,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        preview_resp = await client.post(
            "/api/v1/tts/voice-design/previews",
            json={"prompt": "A calm Vietnamese female narrator", "count": 1},
        )

    assert preview_resp.status_code == 201
    session_id = preview_resp.json()["sessionId"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        commit_resp = await client.post(
            f"/api/v1/tts/voice-design/sessions/{session_id}/commit",
            json={"candidateId": "fake", "displayName": "Bad"},
        )

    assert commit_resp.status_code == 400
    detail = commit_resp.json()["detail"]
    assert detail["code"] == "VOICE_DESIGN_CANDIDATE_NOT_FOUND"
