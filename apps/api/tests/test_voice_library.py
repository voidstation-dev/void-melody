from pathlib import Path

import pytest

from app.api.v1.voices import get_custom_voice, list_custom_voices
from app.api.v1.voices import delete_custom_voice
from app.models.custom_voice import CustomVoiceModel
from app.models.tts_job import TTSJobModel
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_custom_voice_library_supports_search_pagination_and_zero_quality(
    async_session, tmp_path: Path
):
    for name, quality in (("Other voice", 88), ("Needle voice", 0)):
        reference = tmp_path / f"{name.replace(' ', '-')}.wav"
        reference.write_bytes(b"reference")
        async_session.add(
            CustomVoiceModel(
                display_name=name,
                reference_audio_path=str(reference),
                transcript="hello",
                consent_given=True,
                status="ready",
                quality_score=quality,
            )
        )
    await async_session.commit()

    result = await list_custom_voices(
        session=async_session,
        q="needle",
        page=1,
        page_size=20,
    )

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].display_name == "Needle voice"
    assert result.items[0].quality_score == 0


@pytest.mark.asyncio
async def test_custom_voice_library_can_fetch_one_profile(async_session, tmp_path: Path):
    reference = tmp_path / "single.wav"
    reference.write_bytes(b"reference")
    voice = CustomVoiceModel(
        display_name="Single voice",
        reference_audio_path=str(reference),
        transcript="hello",
        consent_given=True,
        status="ready",
    )
    async_session.add(voice)
    await async_session.commit()
    await async_session.refresh(voice)

    result = await get_custom_voice(voice.id, session=async_session)

    assert result.id == voice.id
    assert result.display_name == "Single voice"


@pytest.mark.asyncio
async def test_custom_voice_delete_is_blocked_while_job_is_queued(async_session, tmp_path: Path):
    reference = tmp_path / "queued.wav"
    reference.write_bytes(b"reference")
    voice = CustomVoiceModel(
        display_name="Queued voice",
        reference_audio_path=str(reference),
        transcript="hello",
        consent_given=True,
        status="ready",
    )
    async_session.add(voice)
    await async_session.flush()
    async_session.add(
        TTSJobModel(
            text="hello",
            text_hash="queued-hash",
            voice_type=voice.id,
            voice_display_name=voice.display_name,
            language_code="vi-VN",
            status="queued",
        )
    )
    await async_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await delete_custom_voice(voice.id, session=async_session)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "VOICE_IN_USE"
    assert reference.exists()
