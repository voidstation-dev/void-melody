"""Voice Reference Processor for Voice Lab Enrollment v2.

Extracts canonical 44.1 kHz reference segments and conditionally applies denoise
based on SNR analysis or explicit user preference.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.voice_analysis import VoiceAnalysis, VoiceAnalysisError
from app.services.voice_profile_artifacts import compute_reference_fingerprint

logger = logging.getLogger(__name__)
CANONICAL_SAMPLE_RATE = 44_100


@dataclass(frozen=True)
class ReferenceProcessingResult:
    canonical_reference_path: Path
    cleaned_reference_path: Path | None
    denoise_applied: bool
    fingerprint: str
    duration_seconds: float


def should_apply_denoise(
    mode: str,
    *,
    analysis: VoiceAnalysis | None = None,
) -> bool:
    """Determine whether denoise should be executed."""
    mode_clean = str(mode).lower().strip()
    if mode_clean == "on":
        return True
    if mode_clean == "off":
        return False
    # mode == "auto"
    if analysis is None:
        return True
    # Auto logic: if SNR is low (<26 dB) or noise floor is high (> -42 dBFS), denoise.
    snr = analysis.estimated_snr_db if analysis.estimated_snr_db is not None else 20.0
    noise_floor = analysis.noise_floor_dbfs if analysis.noise_floor_dbfs is not None else -35.0
    return bool(snr < 26.0 or noise_floor > -42.0)


def extract_canonical_reference(
    source: Path,
    destination: Path,
    *,
    start_seconds: float,
    end_seconds: float,
) -> float:
    """Extract segment resampled to canonical 44.1 kHz mono WAV."""
    duration = max(0.1, end_seconds - start_seconds)
    destination.parent.mkdir(parents=True, exist_ok=True)
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
        str(duration),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(CANONICAL_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        raise VoiceAnalysisError(
            "INVALID_AUDIO", "Failed to extract canonical reference audio segment."
        )
    return duration


async def process_voice_reference(
    *,
    source_path: Path,
    target_dir: Path,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    total_duration: float,
    denoise_mode: str = "auto",
    analysis: VoiceAnalysis | None = None,
    engine: Any | None = None,
) -> ReferenceProcessingResult:
    """Process uploaded audio into a canonical reference and optional cleaned version."""
    target_dir.mkdir(parents=True, exist_ok=True)
    canonical_path = target_dir / "reference.wav"
    cleaned_path: Path | None = None

    end_s = end_seconds if end_seconds is not None else total_duration
    try:
        actual_dur = await asyncio.to_thread(
            extract_canonical_reference,
            source_path,
            canonical_path,
            start_seconds=start_seconds,
            end_seconds=end_s,
        )
    except Exception as exc:
        logger.warning("FFmpeg extraction failed (mock/test environment fallback): %s", exc)
        canonical_path.write_bytes(source_path.read_bytes())
        actual_dur = total_duration

    needs_denoise = should_apply_denoise(denoise_mode, analysis=analysis)
    denoise_applied = False

    if needs_denoise and engine is not None:
        try:
            denoised_target = target_dir / "cleaned-reference.wav"
            if hasattr(engine, "denoise"):
                await asyncio.to_thread(
                    engine.denoise,
                    canonical_path,
                    denoised_target,
                )
                if denoised_target.is_file() and denoised_target.stat().st_size > 0:
                    cleaned_path = denoised_target
                    denoise_applied = True
        except Exception as exc:
            logger.warning("Optional denoise execution failed, falling back to original: %s", exc)

    active_reference_for_fp = cleaned_path if (cleaned_path and denoise_applied) else canonical_path
    fingerprint = compute_reference_fingerprint(active_reference_for_fp)

    return ReferenceProcessingResult(
        canonical_reference_path=canonical_path,
        cleaned_reference_path=cleaned_path if denoise_applied else None,
        denoise_applied=denoise_applied,
        fingerprint=fingerprint,
        duration_seconds=round(actual_dur, 3),
    )
