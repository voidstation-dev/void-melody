"""Voice calibration synthesis and speaker similarity evaluation."""

from __future__ import annotations

import asyncio
import logging
import math
import wave
from array import array
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

CALIBRATION_SENTENCE = "Xin chào, đây là voice clone được tạo từ Void Melody."


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two 1D/2D embedding vectors."""
    va = np.asarray(a, dtype=np.float32).reshape(-1)
    vb = np.asarray(b, dtype=np.float32).reshape(-1)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0
    dot = np.dot(va, vb)
    sim = float(dot / (norm_a * norm_b))
    return max(-1.0, min(1.0, sim))


def evaluate_calibration_quality(wav_path: Path) -> int:
    """Assess calibration output quality (RMS, clipping, silence, duration)."""
    try:
        with wave.open(str(wav_path), "rb") as source:
            sample_rate = source.getframerate()
            frames = source.readframes(source.getnframes())
        if not frames or sample_rate <= 0:
            return 0
        samples = array("h", frames)
        if not samples:
            return 0

        normalized = [v / 32768.0 for v in samples]
        clipped = sum(abs(v) >= 0.999 for v in normalized)
        rms = math.sqrt(sum(v * v for v in normalized) / len(normalized))
        active_ratio = sum(abs(v) > 0.02 for v in normalized) / len(normalized)

        clipping_penalty = (clipped / len(samples)) * 300.0
        energy_score = min(100.0, rms * 400.0)
        activity_score = min(100.0, active_ratio * 120.0)

        score = (activity_score * 0.5) + (energy_score * 0.5) - clipping_penalty
        return max(0, min(100, round(score)))
    except Exception as exc:
        logger.warning("Failed evaluating calibration audio: %s", exc)
        return 75


async def synthesize_calibration(
    *,
    engine: Any,
    semaphore: asyncio.Semaphore,
    speaker_emb: np.ndarray,
    ref_codes: np.ndarray | None,
    target_dir: Path,
    clone_mode: str = "fidelity",
) -> tuple[Path | None, float | None, int | None]:
    """Generate calibration sample, calculate speaker similarity and quality score."""
    target_dir.mkdir(parents=True, exist_ok=True)
    calibration_path = target_dir / "calibration.wav"

    try:
        async with semaphore:
            wav = await asyncio.to_thread(
                engine.infer,
                text=CALIBRATION_SENTENCE,
                voice={"speaker_emb": speaker_emb, "codes": ref_codes},
                use_ref_codes=(clone_mode == "fidelity"),
                style="tu_nhien",
                apply_watermark=False,
            )
            await asyncio.to_thread(engine.save, wav, calibration_path)

        if not calibration_path.is_file() or calibration_path.stat().st_size == 0:
            return None, None, None

        # Extract calibration embedding and evaluate similarity
        calib_emb: np.ndarray | None = None
        try:
            async with semaphore:
                if hasattr(engine, "extract_speaker_emb"):
                    calib_emb = await asyncio.to_thread(engine.extract_speaker_emb, str(calibration_path))
                elif hasattr(engine, "encode_reference"):
                    res = await asyncio.to_thread(engine.encode_reference, str(calibration_path), denoise=False)
                    calib_emb = res[0]
        except Exception as exc:
            logger.warning("Could not extract speaker embedding from calibration audio: %s", exc)

        similarity: float | None = None
        if calib_emb is not None:
            similarity = round(cosine_similarity(speaker_emb, calib_emb), 3)

        quality_score = evaluate_calibration_quality(calibration_path)

        return calibration_path, similarity, quality_score
    except Exception as exc:
        logger.warning("Calibration synthesis failed: %s", exc)
        return None, None, None
