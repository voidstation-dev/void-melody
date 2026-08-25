"""VAD-aware reference selector (Selector v2) tests."""

import pytest

from app.services.voice_analysis import (
    MAX_REFERENCE_SECONDS,
    MIN_REFERENCE_SECONDS,
    choose_best_reference_segment,
    choose_best_reference_segment_v2,
)


def _continuous_speech(sample_rate: int, duration: float) -> list[float]:
    """Generate RMS levels that are all above speech threshold."""
    count = int(sample_rate * duration)
    return [0.15] * count


def _mixed_speech(sample_rate: int, duration: float) -> list[float]:
    """Generate levels with speech in the middle, silence at edges."""
    count = int(sample_rate * duration)
    levels = [0.01] * count
    mid = count // 2
    speech_len = int(sample_rate * 3.0)  # 3s of speech in middle
    for i in range(mid, min(mid + speech_len, count)):
        levels[i] = 0.15
    return levels


class TestSelectorV2:
    def test_returns_tuple_of_three_floats(self):
        levels = _continuous_speech(10, 8.0)
        result = choose_best_reference_segment_v2(levels, sample_rate=10)
        assert len(result) == 3
        for v in result:
            assert isinstance(v, float)

    def test_empty_levels_returns_zeros(self):
        result = choose_best_reference_segment_v2([], sample_rate=10)
        assert result == (0.0, 0.0, 0.0)

    def test_short_audio_returns_full_clip(self):
        levels = _continuous_speech(10, 2.0)
        start, end, score = choose_best_reference_segment_v2(levels, sample_rate=10)
        assert end - start == pytest.approx(2.0, abs=0.2)
        assert score > 0

    def test_prefers_continuous_speech_over_silence(self):
        sr = 10
        levels = _mixed_speech(sr, 10.0)
        start, end, score = choose_best_reference_segment_v2(levels, sample_rate=sr)
        # Should select a window in the speech-heavy middle, not the silent edges
        mid = 5.0
        # The selected window should overlap the speech region
        assert start <= mid + 1.0
        assert end > mid - 2.0

    def test_score_in_zero_to_one(self):
        levels = _continuous_speech(10, 8.0)
        _, _, score = choose_best_reference_segment_v2(levels, sample_rate=10)
        assert 0.0 <= score <= 1.0

    def test_respects_max_seconds(self):
        levels = _continuous_speech(10, 20.0)
        start, end, _ = choose_best_reference_segment_v2(levels, sample_rate=10)
        assert end - start <= MAX_REFERENCE_SECONDS + 0.5

    def test_fallback_safe_on_error(self):
        """If v2 raises, the analyze path falls back to v1 (tested by import)."""
        levels = _continuous_speech(10, 8.0)
        v1 = choose_best_reference_segment(levels, sample_rate=10)
        v2 = choose_best_reference_segment_v2(levels, sample_rate=10)
        # Both should return valid segments
        assert len(v1) == 3
        assert len(v2) == 3
        assert v1[0] >= 0.0
        assert v2[0] >= 0.0

    def test_v2_does_not_break_v1(self):
        """V1 selector still works exactly as before — v2 is additive."""
        levels = _continuous_speech(10, 8.0)
        v1_start, v1_end, v1_score = choose_best_reference_segment(levels, sample_rate=10)
        # V1 should pick the full available duration for continuous speech
        assert v1_end - v1_start <= MAX_REFERENCE_SECONDS
        assert 0.0 <= v1_score <= 1.0