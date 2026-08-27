"""Reference transcript capability policy and validation tests (V4-ready)."""

from unittest.mock import patch

import io
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vieneu_core.capabilities import RuntimeCapabilities

from app.database import Base, get_async_session
from app.main import app

test_engine = create_async_engine(
    "sqlite+aiosqlite:///file:memdb_ref_transcript?mode=memory&cache=shared&uri=true",
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_async_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    app.dependency_overrides[get_async_session] = override_get_async_session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.fixture
def enable_clone_runtime(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.voices._clone_runtime_capabilities",
        lambda: RuntimeCapabilities(
            runtime_available=True,
            supports_preset_voices=True,
            supports_voice_cloning=True,
            supports_denoise=True,
            supports_streaming=True,
            reference_text_policy="optional",
            reference_text_used_for_enrollment=False,
            reference_min_seconds=3.0,
            reference_max_seconds=8.0,
        ),
    )

    async def fake_preflight(_reference_path):
        return None

    monkeypatch.setattr("app.api.v1.voices.preflight_clone_reference", fake_preflight)


@pytest.fixture
def enable_required_transcript_runtime(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.voices._clone_runtime_capabilities",
        lambda: RuntimeCapabilities(
            runtime_available=True,
            supports_preset_voices=True,
            supports_voice_cloning=True,
            supports_denoise=True,
            supports_streaming=True,
            reference_text_policy="required",
            reference_text_used_for_enrollment=True,
            reference_min_seconds=3.0,
            reference_max_seconds=8.0,
        ),
    )

    async def fake_preflight(_reference_path):
        return None

    monkeypatch.setattr("app.api.v1.voices.preflight_clone_reference", fake_preflight)


@pytest.mark.asyncio
async def test_capabilities_expose_reference_text_policy():
    """Voice capabilities must expose reference_text_policy and duration limits."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/tts/voices/capabilities",
            headers={"X-Melody-Token": "test-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_text_policy"] == "optional"
    assert payload["reference_text_used_for_enrollment"] is False
    assert payload["reference_min_seconds"] == 3.0
    assert payload["reference_max_seconds"] == 8.0


@pytest.mark.asyncio
async def test_clone_with_transcript_persists_exact_text(enable_clone_runtime):
    """Actual transcript in FormData is persisted on the custom voice profile."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"audio_file": ("test.wav", io.BytesIO(b"fake audio"), "audio/wav")}
        data = {
            "transcript": "Hôm nay tôi muốn kể cho bạn nghe một câu chuyện.",
            "display_name": "Transcript Voice",
            "consent_given": "true",
        }

        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

        assert response.status_code == 201
        payload = response.json()
        assert (
            payload["transcript"]
            == "Hôm nay tôi muốn kể cho bạn nghe một câu chuyện."
        )
        await client.delete(
            f"/api/v1/tts/voices/custom/{payload['id']}",
            headers={"X-Melody-Token": "test-token"},
        )


@pytest.mark.asyncio
async def test_clone_without_transcript_accepted_for_optional_policy(enable_clone_runtime):
    """V3 optional policy: empty transcript is accepted."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"audio_file": ("test.wav", io.BytesIO(b"fake audio"), "audio/wav")}
        data = {
            "display_name": "No Transcript Voice",
            "consent_given": "true",
        }

        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

        assert response.status_code == 201
        # Empty transcript falls back to the placeholder sentinel stored by the orchestrator.
        assert payload_transcript_is_sentinel(response.json()["transcript"])
        voice_id = response.json()["id"]
        await client.delete(
            f"/api/v1/tts/voices/custom/{voice_id}",
            headers={"X-Melody-Token": "test-token"},
        )


def payload_transcript_is_sentinel(transcript: str) -> bool:
    """Orchestrator stores empty transcript as '[reference audio]' sentinel."""
    return transcript == "[reference audio]"


@pytest.mark.asyncio
async def test_required_policy_rejects_empty_transcript(enable_required_transcript_runtime):
    """Future required-policy engine: empty transcript → 422 REFERENCE_TEXT_REQUIRED."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"audio_file": ("test.wav", io.BytesIO(b"fake audio"), "audio/wav")}
        data = {
            "display_name": "Required Policy Voice",
            "consent_given": "true",
        }

        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "REFERENCE_TEXT_REQUIRED"


@pytest.mark.asyncio
async def test_transcript_max_length_rejected(enable_clone_runtime):
    """Transcript over 2000 chars → 422 REFERENCE_TEXT_TOO_LONG."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"audio_file": ("test.wav", io.BytesIO(b"fake audio"), "audio/wav")}
        data = {
            "transcript": "a" * 2001,
            "display_name": "Long Transcript Voice",
            "consent_given": "true",
        }

        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "REFERENCE_TEXT_TOO_LONG"


@pytest.mark.asyncio
async def test_v3_enrollment_does_not_consume_transcript(enable_clone_runtime):
    """Transcript must NOT be passed to prepare_reference / encode_reference for V3."""
    captured_kwargs: dict = {}

    original_prepare = None

    async def fake_analyze(_path):
        from app.services.voice_analysis import VoiceAnalysis

        return VoiceAnalysis(
            duration_seconds=4.0,
            selected_start_seconds=0.0,
            selected_end_seconds=4.0,
            speech_ratio=0.8,
            noise_level_db=-40,
            clipping_ratio=0.0,
            quality_score=80,
            waveform_peaks=[0.1] * 100,
            warnings=[],
        )

    class FakeEngine:
        version = "v3turbo"

        def prepare_reference(self, audio_path, denoise=False, use_ref_codes=True):
            captured_kwargs["audio_path"] = audio_path
            captured_kwargs["denoise"] = denoise
            captured_kwargs["use_ref_codes"] = use_ref_codes
            import numpy as np

            return np.zeros((192,), dtype=np.float32), None

    class FakeManager:
        async def get_engine(self):
            return FakeEngine()

    fake_manager = FakeManager()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"audio_file": ("test.wav", io.BytesIO(b"fake audio"), "audio/wav")}
        data = {
            "transcript": "Đoạn lời thoại tham chiếu",
            "display_name": "V3 Enrollment Check",
            "consent_given": "true",
        }

        with (
            patch("app.api.v1.voices.get_audio_duration", return_value=4.0),
            patch(
                "app.services.clone_orchestrator.ModelManager",
                return_value=fake_manager,
            ),
            patch(
                "app.services.vieneu_enrollment.ModelManager",
                return_value=fake_manager,
            ),
        ):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

        assert response.status_code == 201
        # prepare_reference must be called with exactly denoise=False, use_ref_codes=True,
        # and NEVER with a transcript kwarg.
        assert "transcript" not in captured_kwargs
        assert captured_kwargs["denoise"] is False
        assert captured_kwargs["use_ref_codes"] is True
        voice_id = response.json()["id"]
        await client.delete(
            f"/api/v1/tts/voices/custom/{voice_id}",
            headers={"X-Melody-Token": "test-token"},
        )


@pytest.mark.asyncio
async def test_existing_profile_with_sentinel_transcript_loads(enable_clone_runtime):
    """An old voice with '[reference audio]' sentinel transcript must still resolve."""
    from app.models.custom_voice import CustomVoiceModel

    async with TestSessionLocal() as session:
        old_voice = CustomVoiceModel(
            id="old-voice-0001",
            display_name="Legacy Voice",
            reference_audio_path="/tmp/legacy.wav",
            transcript="[reference audio]",
            consent_given=True,
            status="ready",
            profile_format_version="reference-v1",
        )
        session.add(old_voice)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/tts/voices/custom/old-voice-0001",
            headers={"X-Melody-Token": "test-token"},
        )

    assert response.status_code == 200
    assert response.json()["transcript"] == "[reference audio]"

    async with TestSessionLocal() as session:
        from sqlalchemy import select

        voice = await session.scalar(
            select(CustomVoiceModel).where(
                CustomVoiceModel.id == "old-voice-0001"
            )
        )
        if voice:
            await session.delete(voice)
            await session.commit()


@pytest.mark.asyncio
async def test_transcript_whitespace_is_normalized(enable_clone_runtime):
    """Leading/trailing whitespace in transcript is stripped before persistence."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        files = {"audio_file": ("test.wav", io.BytesIO(b"fake audio"), "audio/wav")}
        data = {
            "transcript": "   lời thoại với khoảng trắng   ",
            "display_name": "Whitespace Voice",
            "consent_given": "true",
        }

        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

        assert response.status_code == 201
        assert response.json()["transcript"] == "lời thoại với khoảng trắng"
        voice_id = response.json()["id"]
        await client.delete(
            f"/api/v1/tts/voices/custom/{voice_id}",
            headers={"X-Melody-Token": "test-token"},
        )