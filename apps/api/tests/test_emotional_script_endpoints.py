import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_async_session
from app.main import app


@pytest.mark.asyncio
async def test_parse_endpoint_returns_reviewable_document():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/scripts/parse",
            json={
                "content": "Linh: [sợ hãi] Anh có nghe thấy gì không?",
                "format": "auto",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["line_count"] == 1
    assert payload["document"]["scenes"][0]["lines"][0]["delivery"]["intent"] == "fear"


@pytest.mark.asyncio
async def test_script_create_and_revision_conflict_are_exposed_over_api(async_session):
    async def override_session():
        yield async_session

    app.dependency_overrides[get_async_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/scripts",
                json={
                    "document": {
                        "version": 1,
                        "title": "Đêm mưa",
                        "revision": 1,
                        "source": {"type": "quick_text", "original_name": None},
                        "defaults": {"voice_id": None, "global_delivery_prompt": None, "base_rate": 1.0, "pause_profile": "normal"},
                        "speakers": [],
                        "scenes": [{
                            "id": "scene-1",
                            "title": "Cảnh 1",
                            "order": 0,
                            "lines": [{
                                "id": "line-1-1",
                                "order": 0,
                                "speaker_id": None,
                                "text": "Một câu chuyện.",
                                "delivery": {"intent": "neutral", "intensity": 0.5, "nonverbals": [], "pause_before_ms": 0, "pause_after_ms": 0},
                                "source_timing": None,
                            }],
                        }],
                        "warnings": [],
                    }
                },
            )
            assert created.status_code == 201
            script_id = created.json()["id"]
            document = created.json()["document"]
            document["title"] = "Bản sửa"

            updated = await client.patch(
                f"/api/v1/scripts/{script_id}",
                json={"document": document, "expected_revision": 1},
            )
            assert updated.status_code == 200
            assert updated.json()["revision"] == 2

            conflict = await client.patch(
                f"/api/v1/scripts/{script_id}",
                json={"document": document, "expected_revision": 1},
            )
            assert conflict.status_code == 409
            assert conflict.json()["detail"]["code"] == "SCRIPT_REVISION_CONFLICT"
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_render_preflight_creates_script_segments_without_tts_jobs(async_session):
    async def override_session():
        yield async_session

    app.dependency_overrides[get_async_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/v1/scripts",
                json={
                    "document": {
                        "version": 1,
                        "title": "Render test",
                        "revision": 1,
                        "source": {"type": "quick_text"},
                        "defaults": {"voice_id": "Minh Đức", "base_rate": 1.0, "pause_profile": "normal"},
                        "speakers": [],
                        "scenes": [{
                            "id": "scene-1",
                            "title": "Cảnh 1",
                            "order": 0,
                            "lines": [{
                                "id": "line-1-1",
                                "order": 0,
                                "text": "Một câu chuyện.",
                                "delivery": {"intent": "neutral", "intensity": 0.5, "nonverbals": [], "pause_before_ms": 0, "pause_after_ms": 0},
                            }],
                        }],
                    }
                },
            )
            script_id = created.json()["id"]
            render = await client.post(f"/api/v1/scripts/{script_id}/renders", json={"scope": "stale", "output_format": "mp3"})

        assert render.status_code == 201
        payload = render.json()
        assert payload["total_segments"] == 1
        assert payload["segments"][0]["status"] == "pending"
    finally:
        app.dependency_overrides.pop(get_async_session, None)
