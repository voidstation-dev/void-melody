from unittest.mock import AsyncMock

import pytest

from app.api.v1.tts_jobs import create_job_endpoint
from app.models.custom_voice import CustomVoiceModel
from app.schemas.tts import CreateTTSJobRequest


@pytest.mark.asyncio
async def test_custom_voice_uuid_reuses_existing_tts_job_contract(async_session, tmp_path, monkeypatch):
    reference = tmp_path / "voice.wav"
    reference.write_bytes(b"reference")
    voice = CustomVoiceModel(
        display_name="Queue voice",
        reference_audio_path=str(reference),
        transcript="Xin chào",
        consent_given=True,
    )
    async_session.add(voice)
    await async_session.commit()
    await async_session.refresh(voice)
    enqueue = AsyncMock()
    monkeypatch.setattr("app.api.v1.tts_jobs.queue_manager.enqueue", enqueue)

    response = await create_job_endpoint(
        CreateTTSJobRequest(text="Preview text", voiceType=voice.id),
        async_session,
    )

    assert response.jobs[0].voiceType == voice.id
    assert response.jobs[0].providerId == "vieneu"
    enqueue.assert_awaited_once()
