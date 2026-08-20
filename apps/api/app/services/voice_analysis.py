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
MIN_REFERENCE_SECONDS = 1.0
MAX_REFERENCE_SECONDS = 8.0


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


def normalized_extension(filename: str | None) -> str | None:
    if not filename:
        return None
    extension = Path(filename).suffix.lower()
    return extension if extension in SUPPORTED_EXTENSIONS else None


def choose_reference_segment(
    speech_levels: list[float], *, sample_rate: int, window_seconds: float = 6
) -> tuple[float, float]:
    """Pick the highest-energy speech-dense window without exceeding 8 sec."""

    if not speech_levels or sample_rate <= 0:
        return (0.0, 0.0)
    window = max(1, min(int(window_seconds * sample_rate), int(MAX_REFERENCE_SECONDS * sample_rate)))
    if len(speech_levels) <= window:
        return (0.0, len(speech_levels) / sample_rate)

    best_start = 0
    best_score = float("-inf")
    for start in range(0, len(speech_levels) - window + 1):
        window_values = speech_levels[start : start + window]
        speech_density = sum(value > 0.02 for value in window_values) / window
        energy = sum(window_values) / window
        score = speech_density * 2.0 + energy
        if score > best_score:
            best_score = score
            best_start = start
    return (best_start / sample_rate, (best_start + window) / sample_rate)


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


def _read_levels(path: Path) -> tuple[float, list[float], float, float, float]:
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
    speech_ratio = sum(level > 0.02 for level in levels) / max(1, len(levels))
    rms = math.sqrt(sum((value / 32768.0) ** 2 for value in samples) / len(samples))
    noise_db = 20 * math.log10(max(rms * 0.2, 1e-6))
    clipping_ratio = clipped / len(samples)
    return duration, levels, speech_ratio, noise_db, clipping_ratio


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
        duration, levels, speech_ratio, noise_db, clipping_ratio = _read_levels(normalized)
        if duration < MIN_REFERENCE_SECONDS:
            raise VoiceAnalysisError("TOO_SHORT", "Audio must be at least one second long.")
        start, end = choose_reference_segment(levels, sample_rate=10)
        warnings: list[str] = []
        if speech_ratio < 0.25:
            warnings.append("Little speech was detected in this sample.")
        if clipping_ratio > 0.01:
            warnings.append("The sample contains clipped audio.")
        if duration > MAX_REFERENCE_SECONDS:
            warnings.append("A shorter speech-dense segment will be used for cloning.")
        quality = round(max(0, min(100, speech_ratio * 70 + max(0, 1 + noise_db / 60) * 25 - clipping_ratio * 500)))
        return VoiceAnalysis(
            duration_seconds=round(duration, 3),
            selected_start_seconds=round(start, 3),
            selected_end_seconds=round(min(end, duration), 3),
            speech_ratio=round(speech_ratio, 3),
            noise_level_db=round(noise_db, 2),
            clipping_ratio=round(clipping_ratio, 5),
            quality_score=quality,
            waveform_peaks=_waveform_peaks(normalized),
            warnings=warnings,
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
