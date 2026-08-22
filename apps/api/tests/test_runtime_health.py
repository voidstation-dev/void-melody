import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_runtime_health_reports_status_without_values():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/runtime")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["checks"]["MELODY_API_TOKEN"], bool)
    assert "value" not in body["checks"]
    assert "MELODY_API_TOKEN" not in str(body.get("details", ""))


@pytest.mark.asyncio
async def test_runtime_health_is_public_in_production_and_never_returns_token(
    monkeypatch,
):
    token = "runtime-health-test-token"
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "melody_api_token", token, raising=False)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/runtime")

    assert response.status_code == 200
    assert response.json()["checks"]["MELODY_API_TOKEN"] is True
    assert token not in response.text
