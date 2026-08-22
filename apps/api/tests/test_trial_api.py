import base64
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.trial_domain import TRIAL_DURATION_SECONDS, create_trial_state
from app.services.trial_storage import TrialStateRepository


@pytest.mark.asyncio
async def test_trial_status_is_public_to_the_authenticated_local_app(tmp_path, monkeypatch) -> None:
    key = b"k" * 32
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "melody_api_token", "test-token")
    monkeypatch.setattr(settings, "trial_integrity_key", base64.urlsafe_b64encode(key).decode())
    monkeypatch.setattr(settings, "trial_state_path", tmp_path / "trial-state-v1.json")
    TrialStateRepository(settings.trial_state_path, key).write(
        create_trial_state(first_run_at=int(time.time()), install_id="install-1")
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/trial/status",
            headers={"X-Melody-Token": "test-token"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["can_synthesize"] is True


@pytest.mark.asyncio
async def test_expired_trial_returns_structured_403_before_compute(tmp_path, monkeypatch) -> None:
    key = b"k" * 32
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "melody_api_token", "test-token")
    monkeypatch.setattr(settings, "trial_integrity_key", base64.urlsafe_b64encode(key).decode())
    monkeypatch.setattr(settings, "trial_state_path", tmp_path / "trial-state-v1.json")
    TrialStateRepository(settings.trial_state_path, key).write(
        create_trial_state(
            first_run_at=1_000,
            last_seen_at=1_000 + TRIAL_DURATION_SECONDS + 1,
            install_id="install-1",
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tts/preview",
            headers={"X-Melody-Token": "test-token"},
            json={"text": "Xin chào", "voiceType": "missing-voice"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "TRIAL_EXPIRED"
    assert response.json()["detail"]["code"] == "TRIAL_EXPIRED"


@pytest.mark.asyncio
async def test_phongvu_key_disables_trial_gate_for_runtime_requests(tmp_path, monkeypatch) -> None:
    key = b"k" * 32
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "melody_api_token", "test-token")
    monkeypatch.setattr(settings, "trial_integrity_key", base64.urlsafe_b64encode(key).decode())
    monkeypatch.setattr(settings, "trial_state_path", tmp_path / "trial-state-v1.json")
    TrialStateRepository(settings.trial_state_path, key).write(
        create_trial_state(
            first_run_at=1_000,
            last_seen_at=1_000 + TRIAL_DURATION_SECONDS + 1,
            install_id="install-1",
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/trial/status",
            headers={
                "X-Melody-Token": "test-token",
                "X-Melody-License-Key": "phongvu",
            },
        )

    assert response.status_code == 200
    assert response.json()["can_synthesize"] is True
    assert response.json()["override"] == "phongvu"
