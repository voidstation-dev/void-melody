"""Local reference-audio validation and analysis for Voice Lab.

The service accepts an opaque temporary path, normalizes with the existing
FFmpeg binary, and returns metadata only. User supplied filenames are never
used to construct filesystem paths.
"""

from __future__ import annotations

import asyncio
import math
import subprocess
import uuid
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
ANALYSIS_SAMPLE_RATE = 16_000
MIN_REFERENCE_SECONDS = 3.0
MAX_REFERENCE_SECONDS = 8.0
VAD_SELECTOR_ENABLED = False  # ponytail: flip when speech-worker VAD probe is wired


class VoiceAnalysisError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class VoiceAnalysis:
    duration_seconds: float
    selected_start_seconds: float
    selected_end_seconds: float
    speech_ratio: float
    noise_level_db: float
    clipping_ratio: float
    quality_score: int
    waveform_peaks: list[float]
    warnings: list[str]
    source_duration_seconds: float | None = None
    reference_duration_seconds: float | None = None
    estimated_snr_db: float | None = None
    noise_floor_dbfs: float | None = None
    silence_ratio: float | None = None
    level_stability: float | None = None
    recommended_start_seconds: float | None = None
    recommended_end_seconds: float | None = None
    metrics: dict[str, int] | None = None


def normalized_extension(filename: str | None) -> str | None:
    if not filename:
        return None
    extension = Path(filename).suffix.lower()
    return extension if extension in SUPPORTED_EXTENSIONS else None


def choose_best_reference_segment(
    levels: list[float],
    *,
    sample_rate: int = 10,
    window_seconds: float | None = None,
    min_seconds: float = 5.0,
    max_seconds: float = 8.0,
) -> tuple[float, float, float]:
    """Find the highest quality 5.0 - 8.0s segment using prefix sums.

    Returns: (start_seconds, end_seconds, segment_quality_0_to_1)
    """
    n = len(levels)
    if n == 0 or sample_rate <= 0:
        return 0.0, 0.0, 0.0

    total_duration = n / sample_rate
    effective_min = window_seconds if window_seconds is not None else min_seconds
    if total_duration <= effective_min:
        return 0.0, total_duration, 0.8

    speech_flags = [1 if lvl > 0.02 else 0 for lvl in levels]
    speech_prefix = [0] * (n + 1)
    energy_prefix = [0.0] * (n + 1)
    for i in range(n):
        speech_prefix[i + 1] = speech_prefix[i] + speech_flags[i]
        energy_prefix[i + 1] = energy_prefix[i] + levels[i]

    if window_seconds is not None:
        candidate_durations = [min(window_seconds, MAX_REFERENCE_SECONDS)]
    else:
        candidate_durations = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]

    best_start = 0
    best_dur = min(total_duration, candidate_durations[0])
    best_score = float("-inf")

    for dur in candidate_durations:
        win = int(round(dur * sample_rate))
        if win > n:
            continue
        for start in range(0, n - win + 1):
            speech_cnt = speech_prefix[start + win] - speech_prefix[start]
            speech_cov = speech_cnt / win
            energy_sum = energy_prefix[start + win] - energy_prefix[start]
            avg_energy = energy_sum / win

            sweet_spot_bonus = 0.15 if (window_seconds is None and 5.5 <= dur <= 7.0) else 0.0
            score = (speech_cov * 2.0) + avg_energy + sweet_spot_bonus
            if score > best_score:
                best_score = score
                best_start = start
                best_dur = dur

    norm_score = max(0.0, min(1.0, (best_score + 0.2) / 3.0))
    start_sec = round(best_start / sample_rate, 3)
    end_sec = round(min(total_duration, start_sec + best_dur), 3)
    return start_sec, end_sec, norm_score


def choose_reference_segment(
    speech_levels: list[float], *, sample_rate: int, window_seconds: float = 6
) -> tuple[float, float]:
    """Backward-compatible wrapper picking best segment."""
    start, end, _ = choose_best_reference_segment(
        speech_levels, sample_rate=sample_rate, window_seconds=window_seconds
    )
    return start, end

def choose_best_reference_segment_v2(
    levels: list[float],
    *,
    sample_rate: int = 10,
    min_seconds: float = MIN_REFERENCE_SECONDS,
    max_seconds: float = MAX_REFERENCE_SECONDS,
) -> tuple[float, float, float]:
    """VAD-aware reference segment selector (Selector v2).

    Scores candidate 3–8s windows using:
      speech continuity (fewer silence breaks) + speech ratio + energy
      − silence penalty − boundary-cut penalty − clipping.

    Falls back to choose_best_reference_segment on any edge case so the
    existing path is never broken.
    """
    n = len(levels)
    if n == 0 or sample_rate <= 0:
        return 0.0, 0.0, 0.0

    total_duration = n / sample_rate
    if total_duration <= min_seconds:
        return 0.0, total_duration, 0.8

    speech_flags = [1 if lvl > 0.02 else 0 for lvl in levels]

    speech_prefix = [0] * (n + 1)
    energy_prefix = [0.0] * (n + 1)
    for i in range(n):
        speech_prefix[i + 1] = speech_prefix[i] + speech_flags[i]
        energy_prefix[i + 1] = energy_prefix[i] + levels[i]

    candidate_durations = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
    best_start = 0
    best_dur = min(total_duration, candidate_durations[0])
    best_score = float("-inf")

    for dur in candidate_durations:
        win = int(round(dur * sample_rate))
        if win > n:
            continue
        for start in range(0, n - win + 1):
            end = start + win
            speech_cnt = speech_prefix[end] - speech_prefix[start]
            speech_cov = speech_cnt / win
            energy_sum = energy_prefix[end] - energy_prefix[start]
            avg_energy = energy_sum / win

            # Continuity: count silence→speech transitions inside the window.
            # Fewer breaks = more continuous speech. 0 breaks is ideal.
            breaks = 0
            for j in range(start + 1, end):
                if speech_flags[j] == 1 and speech_flags[j - 1] == 0:
                    breaks += 1
            continuity = max(0.0, 1.0 - (breaks / max(1, win / sample_rate)))

            # Boundary-cut penalty: penalize speech cut at start/end edges.
            boundary_penalty = 0.0
            if speech_flags[start] == 1:
                boundary_penalty += 0.1
            if speech_flags[end - 1] == 1:
                boundary_penalty += 0.1

            # Silence penalty: windows dominated by silence score lower.
            silence_ratio = 1.0 - speech_cov
            silence_penalty = silence_ratio * 0.5

            sweet_spot_bonus = 0.15 if 5.5 <= dur <= 7.0 else 0.0
            score = (
                speech_cov * 1.5
                + continuity * 0.8
                + avg_energy
                - silence_penalty
                - boundary_penalty
                + sweet_spot_bonus
            )
            if score > best_score:
                best_score = score
                best_start = start
                best_dur = dur

    norm_score = max(0.0, min(1.0, (best_score + 0.2) / 3.5))
    start_sec = round(best_start / sample_rate, 3)
    end_sec = round(min(total_duration, start_sec + best_dur), 3)
    return start_sec, end_sec, norm_score


def _normalize_with_ffmpeg(source: Path, destination: Path) -> None:
    command = [
        settings.ffmpeg_binary_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(ANALYSIS_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0 or not destination.exists() or destination.stat().st_size == 0:
        raise VoiceAnalysisError("INVALID_AUDIO", "The file could not be decoded as audio.")


def _read_levels(
    path: Path,
) -> tuple[float, list[float], float, float, float, float, float, float, float]:
    try:
        with wave.open(str(path), "rb") as source:
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
            sample_width = source.getsampwidth()
            frames = source.readframes(frame_count)
    except (OSError, wave.Error) as exc:
        raise VoiceAnalysisError("INVALID_AUDIO", "The normalized audio is invalid.") from exc

    if sample_width != 2:
        raise VoiceAnalysisError("INVALID_AUDIO", "The normalized audio format is unsupported.")
    samples = array("h", frames)
    if not samples or sample_rate <= 0:
        raise VoiceAnalysisError("INVALID_AUDIO", "The audio file is empty.")

    # 100ms analysis window
    window_size = max(1, sample_rate // 10)
    levels: list[float] = []
    clipped = 0
    for index in range(0, len(samples), window_size):
        window = samples[index : index + window_size]
        if not window:
            continue
        normalized = [value / 32768.0 for value in window]
        clipped += sum(abs(value) >= 0.999 for value in normalized)
        rms = math.sqrt(sum(value * value for value in normalized) / len(normalized))
        levels.append(rms)

    duration = len(samples) / sample_rate
    active_speech_levels = [lvl for lvl in levels if lvl > 0.02]
    speech_ratio = len(active_speech_levels) / max(1, len(levels))
    silence_ratio = 1.0 - speech_ratio
    clipping_ratio = clipped / len(samples)

    # Noise floor & SNR via percentile estimates
    sorted_levels = sorted(levels)
    noise_idx = max(0, int(len(sorted_levels) * 0.10))
    noise_floor_rms = max(1e-5, sorted_levels[noise_idx])
    noise_floor_dbfs = 20.0 * math.log10(noise_floor_rms)

    if active_speech_levels:
        sorted_active = sorted(active_speech_levels)
        speech_idx = max(0, int(len(sorted_active) * 0.85))
        speech_level_rms = sorted_active[speech_idx]
        speech_level_dbfs = 20.0 * math.log10(max(1e-5, speech_level_rms))
        estimated_snr_db = max(0.0, speech_level_dbfs - noise_floor_dbfs)

        mean_active = sum(active_speech_levels) / len(active_speech_levels)
        variance = sum((lvl - mean_active) ** 2 for lvl in active_speech_levels) / len(active_speech_levels)
        std_dev = math.sqrt(variance)
        level_stability = max(0.0, min(1.0, 1.0 - (std_dev / max(1e-4, mean_active))))
    else:
        estimated_snr_db = 0.0
        level_stability = 0.0

    # General noise_level_db for backward compatibility
    overall_rms = math.sqrt(sum((v / 32768.0) ** 2 for v in samples) / len(samples))
    noise_db = 20.0 * math.log10(max(overall_rms * 0.2, 1e-6))

    return (
        duration,
        levels,
        speech_ratio,
        noise_db,
        clipping_ratio,
        estimated_snr_db,
        noise_floor_dbfs,
        silence_ratio,
        level_stability,
    )


def _waveform_peaks(path: Path, bucket_count: int = 48) -> list[float]:
    with wave.open(str(path), "rb") as source:
        samples = array("h", source.readframes(source.getnframes()))
    if not samples:
        return []
    bucket_size = max(1, math.ceil(len(samples) / bucket_count))
    return [
        round(max(abs(value) for value in samples[index : index + bucket_size]) / 32768.0, 4)
        for index in range(0, len(samples), bucket_size)
    ][:bucket_count]


def analyze_audio_file(source: Path) -> VoiceAnalysis:
    normalized = source.with_name(f"{uuid.uuid4().hex}.normalized.wav")
    try:
        _normalize_with_ffmpeg(source, normalized)
        (
            duration,
            levels,
            speech_ratio,
            noise_db,
            clipping_ratio,
            estimated_snr_db,
            noise_floor_dbfs,
            silence_ratio,
            level_stability,
        ) = _read_levels(normalized)

        if duration < MIN_REFERENCE_SECONDS:
            raise VoiceAnalysisError(
                "TOO_SHORT",
                "Audio must be at least three seconds long.",
            )

        if VAD_SELECTOR_ENABLED:
            try:
                start, end, segment_score_norm = choose_best_reference_segment_v2(levels, sample_rate=10)
            except Exception:
                start, end, segment_score_norm = choose_best_reference_segment(levels, sample_rate=10)
        else:
            start, end, segment_score_norm = choose_best_reference_segment(levels, sample_rate=10)

        warnings: list[str] = []
        if speech_ratio < 0.25:
            warnings.append("Little speech was detected in this sample.")
        if clipping_ratio > 0.01:
            warnings.append("The sample contains clipped audio.")
        if estimated_snr_db < 15.0:
            warnings.append("High background noise detected; denoise cleanup is recommended.")
        if duration > MAX_REFERENCE_SECONDS:
            warnings.append("A shorter speech-dense segment will be used for cloning.")

        # Subscores calculation
        speech_score = round(max(0, min(100, speech_ratio * 125)))
        noise_score = round(max(0, min(100, (estimated_snr_db / 32.0) * 100)))
        clipping_score = round(max(0, min(100, (1.0 - clipping_ratio * 50.0) * 100)))
        stability_score = round(max(0, min(100, level_stability * 100)))
        segment_score = round(max(0, min(100, segment_score_norm * 100)))

        overall_quality = round(
            0.35 * speech_score
            + 0.25 * noise_score
            + 0.15 * clipping_score
            + 0.15 * stability_score
            + 0.10 * segment_score
        )
        quality_score = max(0, min(100, overall_quality))

        metrics = {
            "speech_score": speech_score,
            "noise_score": noise_score,
            "clipping_score": clipping_score,
            "stability_score": stability_score,
            "segment_score": segment_score,
        }

        return VoiceAnalysis(
            duration_seconds=round(duration, 3),
            selected_start_seconds=round(start, 3),
            selected_end_seconds=round(min(end, duration), 3),
            speech_ratio=round(speech_ratio, 3),
            noise_level_db=round(noise_db, 2),
            clipping_ratio=round(clipping_ratio, 5),
            quality_score=quality_score,
            waveform_peaks=_waveform_peaks(normalized),
            warnings=warnings,
            source_duration_seconds=round(duration, 3),
            reference_duration_seconds=round(min(end, duration) - start, 3),
            estimated_snr_db=round(estimated_snr_db, 1),
            noise_floor_dbfs=round(noise_floor_dbfs, 1),
            silence_ratio=round(silence_ratio, 3),
            level_stability=round(level_stability, 3),
            recommended_start_seconds=round(start, 3),
            recommended_end_seconds=round(min(end, duration), 3),
            metrics=metrics,
        )
    finally:
        normalized.unlink(missing_ok=True)


async def analyze_audio_file_async(source: Path) -> VoiceAnalysis:
    return await asyncio.to_thread(analyze_audio_file, source)


def validate_reference_selection(
    start_seconds: float | None,
    end_seconds: float | None,
    *,
    duration_seconds: float,
) -> tuple[float, float] | None:
    if start_seconds is None and end_seconds is None:
        return None
    if start_seconds is None or end_seconds is None:
        raise VoiceAnalysisError("INVALID_SEGMENT", "Reference segment start and end are required.")
    if not math.isfinite(start_seconds) or not math.isfinite(end_seconds):
        raise VoiceAnalysisError("INVALID_SEGMENT", "Reference segment timestamps are invalid.")
    if start_seconds < 0 or end_seconds <= start_seconds:
        raise VoiceAnalysisError("INVALID_SEGMENT", "Reference segment timestamps are invalid.")
    if end_seconds > duration_seconds + 0.01:
        raise VoiceAnalysisError("INVALID_SEGMENT", "Reference segment exceeds the source duration.")
    if end_seconds - start_seconds > MAX_REFERENCE_SECONDS + 0.01:
        raise VoiceAnalysisError("INVALID_SEGMENT", "Reference segment cannot exceed 8 seconds.")
    if end_seconds - start_seconds < MIN_REFERENCE_SECONDS:
        raise VoiceAnalysisError("INVALID_SEGMENT", "Reference segment must be at least 3 seconds.")
    return (round(start_seconds, 3), round(min(end_seconds, duration_seconds), 3))


def extract_reference_segment(
    source: Path,
    destination: Path,
    *,
    start_seconds: float,
    end_seconds: float,
) -> None:
    """Create the bounded, canonical WAV used by the clone provider."""

    command = [
        settings.ffmpeg_binary_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(start_seconds),
        "-i",
        str(source),
        "-t",
        str(end_seconds - start_seconds),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(ANALYSIS_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0 or not destination.exists() or destination.stat().st_size == 0:
        raise VoiceAnalysisError("INVALID_AUDIO", "The selected reference segment could not be decoded.")


async def extract_reference_segment_async(
    source: Path,
    destination: Path,
    *,
    start_seconds: float,
    end_seconds: float,
) -> None:
    await asyncio.to_thread(
        extract_reference_segment,
        source,
        destination,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )


async def save_upload_to_temp(upload, *, directory: Path, max_bytes: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"analysis-{uuid.uuid4().hex}.input"
    total = 0
    try:
        with path.open("wb") as destination:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise VoiceAnalysisError("FILE_TOO_LARGE", "Audio file exceeds the upload limit.")
                destination.write(chunk)
        if total == 0:
            raise VoiceAnalysisError("EMPTY_FILE", "Audio file is empty.")
        return path
    except BaseException:
        path.unlink(missing_ok=True)
        raise
