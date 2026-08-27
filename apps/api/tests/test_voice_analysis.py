import io
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.voice_analysis import (
    VoiceAnalysis,
    VoiceAnalysisError,
    choose_reference_segment,
    normalized_extension,
    validate_reference_selection,
)


def test_normalized_extension_never_uses_raw_filename_as_a_path():
    assert normalized_extension("../../voice.wav") == ".wav"
    assert normalized_extension("voice.MP3") == ".mp3"
    assert normalized_extension("voice.wav.exe") is None


def test_best_reference_segment_prefers_speech_dense_window():
    speech = [0.001] * 8 + [0.2] * 6 + [0.001] * 8

    start, end = choose_reference_segment(speech, sample_rate=1, window_seconds=6)

    assert (start, end) == (8.0, 14.0)


def test_short_source_is_not_silently_expanded():
    start, end = choose_reference_segment([0.2, 0.2], sample_rate=1, window_seconds=6)

    assert (start, end) == (0.0, 2.0)


def test_reference_selection_is_bounded_to_the_source_and_eight_seconds():
    assert validate_reference_selection(2.0, 8.0, duration_seconds=12.0) == (2.0, 8.0)
    assert validate_reference_selection(0.0, 3.0, duration_seconds=12.0) == (0.0, 3.0)

    with pytest.raises(VoiceAnalysisError, match="3 seconds"):
        validate_reference_selection(0.0, 2.99, duration_seconds=12.0)

    with pytest.raises(VoiceAnalysisError, match="8 seconds"):
        validate_reference_selection(0.0, 9.0, duration_seconds=12.0)

    with pytest.raises(VoiceAnalysisError, match="duration"):
        validate_reference_selection(6.0, 13.0, duration_seconds=12.0)


@pytest.mark.asyncio
async def test_analyze_rejects_extension_without_touching_backend():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tts/voices/analyze",
            files={"audio_file": ("voice.exe", io.BytesIO(b"not audio"), "application/octet-stream")},
            headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FORMAT"


@pytest.mark.asyncio
async def test_analyze_returns_path_free_metadata():
    analysis = VoiceAnalysis(
        duration_seconds=12.0,
        selected_start_seconds=2.0,
        selected_end_seconds=8.0,
        speech_ratio=0.8,
        noise_level_db=-42.0,
        clipping_ratio=0.0,
        quality_score=92,
        waveform_peaks=[0.1, 0.2],
        warnings=[],
    )
    with patch("app.api.v1.voices.analyze_audio_file_async", return_value=analysis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tts/voices/analyze",
                files={"audio_file": ("../../voice.wav", io.BytesIO(b"fake"), "audio/wav")},
                headers={"X-Melody-Token": "test-token", "X-License-Key": "dev"},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["quality_score"] == 92
    assert "path" not in payload
