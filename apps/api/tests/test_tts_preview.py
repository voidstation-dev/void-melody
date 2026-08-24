import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_tts_preview_capcut():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/tts/preview",
            json={"text": "Xin chao", "voiceType": "BV421_vivn_streaming", "rate": 1.0},
        )
        print("Status code:", response.status_code)
        print("Content length:", len(response.content))
        print("Content-type:", response.headers.get("content-type"))
        assert response.status_code == 200
        assert len(response.content) > 0
        assert response.headers.get("content-type") == "audio/mpeg"
