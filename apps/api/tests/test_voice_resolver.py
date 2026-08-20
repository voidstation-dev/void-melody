from pathlib import Path

import pytest

from app.models.custom_voice import CustomVoiceModel
from app.services.voice_resolver import VoiceResolutionError, resolve_voice


@pytest.mark.asyncio
async def test_resolver_returns_normalized_custom_voice_descriptor(async_session, tmp_path: Path):
    reference = tmp_path / "custom.wav"
    reference.write_bytes(b"reference")
    voice = CustomVoiceModel(
        display_name="Resolver voice",
        reference_audio_path=str(reference),
        transcript="hello",
        consent_given=True,
        status="ready",
    )
    async_session.add(voice)
    await async_session.commit()
    await async_session.refresh(voice)

    resolved = await resolve_voice(async_session, voice.id)

    assert resolved.voice_type == voice.id
    assert resolved.display_name == "Resolver voice"
    assert resolved.provider_id == "vieneu"
    assert resolved.source == "custom"
    assert resolved.status == "ready"


@pytest.mark.asyncio
async def test_resolver_rejects_custom_voice_with_missing_reference(async_session, tmp_path: Path):
    voice = CustomVoiceModel(
        display_name="Missing resolver voice",
        reference_audio_path=str(tmp_path / "missing.wav"),
        transcript="hello",
        consent_given=True,
        status="ready",
    )
    async_session.add(voice)
    await async_session.commit()
    await async_session.refresh(voice)

    with pytest.raises(VoiceResolutionError, match="reference audio is missing") as exc_info:
        await resolve_voice(async_session, voice.id)

    assert exc_info.value.code == "VOICE_REFERENCE_MISSING"
