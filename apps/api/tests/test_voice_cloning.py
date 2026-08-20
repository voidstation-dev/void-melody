import io
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_async_session
from app.main import app

# Create a test database engine
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

async def override_get_async_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.mark.asyncio
async def test_voice_capabilities_report_runtime_gate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/tts/voices/capabilities",
            headers={"X-Melody-Token": "test-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_id"] == "vieneu"
    assert payload["engine_id"] == "v3turbo"
    assert "supports_voice_cloning" in payload
    assert "reason_code" in payload

@pytest.mark.asyncio
async def test_clone_voice_no_consent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        file_content = b"fake audio content"
        files = {"audio_file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
        data = {
            "transcript": "Hello world",
            "display_name": "My Voice",
            "consent_given": "false",
        }
        response = await client.post(
            "/api/v1/tts/voices/clone",
            data=data,
            files=files,
            headers={"X-Melody-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "consent" in response.json()["detail"]


@pytest.mark.asyncio
async def test_clone_voice_invalid_extension():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        file_content = b"fake audio content"
        files = {"audio_file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {
            "transcript": "Hello world",
            "display_name": "My Voice",
            "consent_given": "true",
        }
        response = await client.post(
            "/api/v1/tts/voices/clone",
            data=data,
            files=files,
            headers={"X-Melody-Token": "test-token"},
        )
        assert response.status_code == 400
        assert "Unsupported audio format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_clone_voice_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        file_content = b"fake audio content"
        files = {"audio_file": ("test.wav", io.BytesIO(file_content), "audio/wav")}
        data = {
            "transcript": "Hello world",
            "display_name": "My Voice",
            "consent_given": "true",
        }
        
        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token"},
            )
        
        assert response.status_code == 201
        resp_data = response.json()
        assert "id" in resp_data
        assert resp_data["display_name"] == "My Voice"
        assert resp_data["transcript"] == "Hello world"
        assert resp_data["consent_given"] is True

        voice_id = resp_data["id"]

        list_response = await client.get("/api/v1/tts/voices/custom", headers={"X-Melody-Token": "test-token"})
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] >= 1
        assert any(v["id"] == voice_id for v in list_data["items"])

        delete_response = await client.delete(f"/api/v1/tts/voices/custom/{voice_id}", headers={"X-Melody-Token": "test-token"})
        assert delete_response.status_code == 204

        list_response2 = await client.get("/api/v1/tts/voices/custom", headers={"X-Melody-Token": "test-token"})
        assert not any(v["id"] == voice_id for v in list_response2.json()["items"])


@pytest.mark.asyncio
async def test_clone_voice_does_not_use_user_filename_as_temp_path():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"audio_file": ("../../voice.wav", io.BytesIO(b"fake audio content"), "audio/wav")}
        data = {"transcript": "Hello world", "display_name": "Safe Voice", "consent_given": "true"}
        with patch("app.api.v1.voices.get_audio_duration", return_value=4.0):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token"},
            )

        assert response.status_code == 201
        voice_id = response.json()["id"]
        assert response.json()["status"] == "ready"
        await client.delete(f"/api/v1/tts/voices/custom/{voice_id}", headers={"X-Melody-Token": "test-token"})


@pytest.mark.asyncio
async def test_clone_voice_uses_selected_segment_for_long_source():
    async def fake_extract(_source, destination, *, start_seconds, end_seconds):
        assert (start_seconds, end_seconds) == (2.0, 8.0)
        destination.write_bytes(b"selected reference")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"audio_file": ("long.wav", io.BytesIO(b"fake audio content"), "audio/wav")}
        data = {
            "display_name": "Selected Voice",
            "consent_given": "true",
            "selected_start_seconds": "2",
            "selected_end_seconds": "8",
        }
        with (
            patch("app.api.v1.voices.get_audio_duration", return_value=12.0),
            patch("app.api.v1.voices.extract_reference_segment_async", side_effect=fake_extract),
        ):
            response = await client.post(
                "/api/v1/tts/voices/clone",
                data=data,
                files=files,
                headers={"X-Melody-Token": "test-token"},
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["selected_start_seconds"] == 2.0
        assert payload["selected_end_seconds"] == 8.0
        await client.delete(f"/api/v1/tts/voices/custom/{payload['id']}", headers={"X-Melody-Token": "test-token"})
