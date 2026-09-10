"""Real VoxCPM2 backend.

Implemented in Phase 4: neutral cloning only. The voxcpm import is deferred
until load_model so the module is safe to import (and test) without the
package installed. Never falls back to the mock backend.

Requires the voxcpm package in a dedicated worker environment
(Python >=3.10,<3.13 + torch >=2.5) — never the FastAPI main environment.
"""

from __future__ import annotations

import logging
import struct
import wave
from pathlib import Path
from typing import Any

import numpy as np

from backend import VoxCpmBackend
from errors import (
    VOXCPM_INFERENCE_FAILED,
    VOXCPM_INVALID_PARAMS,
    VOXCPM_MODEL_NOT_LOADED,
    VOXCPM_PACKAGE_NOT_INSTALLED,
    VOXCPM_REFERENCE_INVALID,
    WorkerError,
)
from path_utils import validate_path

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "openbmb/VoxCPM2"
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_CFG_VALUE = 2.0
DEFAULT_INFERENCE_TIMESTEPS = 10

# Phase 5: emotion presets compiled to natural-language instructions.
# Plan rule: presets are NOT engine enums — each maps to a performance
# instruction; identity comes from the reference audio, instruction is the
# performance.
EMOTION_PRESET_INSTRUCTIONS: dict[str, str] = {
    "neutral": "",
    "cheerful": "Cheerful, bright and upbeat, lively pacing, warm smiling tone",
    "excited": "Excited and energetic, fast enthusiastic pacing, elevated volume",
    "sad": "Sad, restrained, speaking slowly, soft volume, trying not to cry",
    "angry": "Angry, tense and sharp, clipped aggressive delivery",
    "fearful": "Fearful and anxious, trembling hesitant voice, uneven pacing",
    "gentle": "Gentle and tender, soft volume, slow soothing pacing",
    "whisper": "Whispered, very soft breathy voice, close intimate delivery",
    "calm": "Calm and steady, even relaxed pacing, neutral soft volume",
    "storytelling": "Warm storytelling narration, expressive measured pacing, drawing the listener in",
}


def _import_error() -> Exception | None:
    try:
        import voxcpm  # noqa: F401

        return None
    except Exception as exc:  # pragma: no cover - exercised only without the package
        return exc


class RealVoxCpmBackend(VoxCpmBackend):
    """Backend delegating to the installed voxcpm package (neutral clone only)."""

    def __init__(self) -> None:
        self.model: Any | None = None
        self.device: str = "cpu"
        self.model_id: str = DEFAULT_MODEL_ID
        self.sample_rate: int = DEFAULT_SAMPLE_RATE
        self._import_error: Exception | None = _import_error()

    # ---- contract methods ----

    def ping(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"pong": True, "mock": False, "mode": "real"}

    def runtime_info(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ready": self.model is not None,
            "model_loaded": self.model is not None,
            "device": self.device,
            "backend": "real",
            "sample_rate": self.sample_rate,
            "model_id": self.model_id,
            "package_installed": self._import_error is None,
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._import_error is not None:
            raise WorkerError(
                VOXCPM_PACKAGE_NOT_INSTALLED,
                f"Failed to import voxcpm: {self._import_error}",
            )

        model_id = params.get("model_id", DEFAULT_MODEL_ID)
        device = params.get("device", "auto")

        # Deferred heavy import — happens only on first load.
        from voxcpm import VoxCPM  # type: ignore[import-not-found]

        load_kwargs: dict[str, Any] = {"load_denoiser": False}
        if device and device != "auto":
            load_kwargs["device"] = device
        try:
            self.model = VoxCPM.from_pretrained(model_id, **load_kwargs)
        except TypeError:
            # Older builds may not accept load_denoiser.
            self.model = VoxCPM.from_pretrained(model_id)

        self.model_id = model_id
        self.device = self._resolve_device()
        self.sample_rate = int(
            getattr(getattr(self.model, "tts_model", None), "sample_rate", DEFAULT_SAMPLE_RATE)
        )
        return {
            "status": "loaded",
            "backend": "real",
            "device": self.device,
            "sample_rate": self.sample_rate,
        }

    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        released = self.model is not None
        self.model = None
        self.device = "cpu"
        return {"status": "unloaded", "backend": "real", "released": released}

    def warmup(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.model is None:
            raise WorkerError(VOXCPM_MODEL_NOT_LOADED, "Model is not loaded.")
        params = params or {}
        reference_wav_path = params.get("reference_wav_path")
        generate_kwargs: dict[str, Any] = {
            "text": "Xin chào.",
            "cfg_value": DEFAULT_CFG_VALUE,
            "inference_timesteps": DEFAULT_INFERENCE_TIMESTEPS,
        }
        if reference_wav_path:
            generate_kwargs["reference_wav_path"] = str(validate_path(reference_wav_path))
        self._generate(generate_kwargs)
        return {"status": "warmed", "backend": "real"}

    def analyze_reference(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = validate_path(params["audio_path"])
        if not audio_path.is_file():
            raise WorkerError(VOXCPM_REFERENCE_INVALID, "Reference audio not found.")
        duration = params.get("duration")
        if duration is None:
            duration = _wav_duration_seconds(audio_path)
        # Neutral clone does not need embedding analysis; report basic truth.
        return {
            "audio_path": str(audio_path),
            "duration_seconds": float(duration or 0.0),
            "sample_rate": self.sample_rate,
            "backend": "real",
        }

    def synthesize_clone(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._synthesize(params, use_reference=True)

    def synthesize_emotional(self, params: dict[str, Any]) -> dict[str, Any]:
        """Phase 5: emotional TTS from a cloned voice.

        reference audio = voice identity; instruction = performance.
        The preset is compiled to a natural-language instruction and wrapped
        around the text: controlled_text = f"({instruction}){text}".
        """
        self._require_model()

        text = params.get("text")
        if not text or not isinstance(text, str):
            raise WorkerError(VOXCPM_INVALID_PARAMS, "Synthesis requires non-empty 'text'.")

        instruction = self._resolve_instruction(params)
        controlled_text = f"({instruction}){text}" if instruction else text

        emotional_params = dict(params)
        emotional_params["text"] = controlled_text
        result = self._synthesize(emotional_params, use_reference=True)
        result["method"] = "synthesize_emotional"
        result["instruction"] = instruction or None
        return result

    def synthesize_ultimate(self, params: dict[str, Any]) -> dict[str, Any]:
        raise WorkerError(
            "VOXCPM_NOT_IMPLEMENTED",
            "Ultimate clone is deferred to Phase 8 (plan: LATER).",
        )

    # ---- internals ----

    def _resolve_instruction(self, params: dict[str, Any]) -> str:
        """Compile an emotion preset / custom instruction to performance text.

        Priority: explicit instruction > emotion preset > neutral (empty).
        """
        instruction = params.get("instruction")
        if isinstance(instruction, str) and instruction.strip():
            return instruction.strip()
        emotion = params.get("emotion")
        if isinstance(emotion, str) and emotion.strip():
            key = emotion.strip().lower()
            if key in EMOTION_PRESET_INSTRUCTIONS:
                return EMOTION_PRESET_INSTRUCTIONS[key]
            raise WorkerError(
                VOXCPM_INVALID_PARAMS,
                f"Unknown emotion preset '{emotion}'. Valid: "
                + ", ".join(sorted(EMOTION_PRESET_INSTRUCTIONS)),
            )
        return ""

    def _resolve_device(self) -> str:
        if self.model is None:
            return "cpu"
        # VoxCPM stores device info loosely; try common attributes.
        for attr in ("device", "_device"):
            device = getattr(self.model, attr, None)
            if device:
                return str(device)
        try:
            import torch  # type: ignore[import-not-found]

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _require_model(self) -> Any:
        if self.model is None:
            raise WorkerError(VOXCPM_MODEL_NOT_LOADED, "Model is not loaded.")
        return self.model

    def _synthesize(self, params: dict[str, Any], *, use_reference: bool = True) -> dict[str, Any]:
        model = self._require_model()

        text = params.get("text")
        if not text or not isinstance(text, str):
            raise WorkerError(VOXCPM_INVALID_PARAMS, "Synthesis requires non-empty 'text'.")

        output_path = validate_path(params["output_path"])
        reference_wav_path = params.get("reference_wav_path")
        if use_reference:
            if not reference_wav_path:
                raise WorkerError(
                    VOXCPM_INVALID_PARAMS,
                    "synthesize_clone requires 'reference_wav_path'.",
                )
            reference_path = Path(reference_wav_path)
            if not reference_path.is_file():
                raise WorkerError(
                    VOXCPM_REFERENCE_INVALID,
                    "Reference audio not found.",
                )
            reference_wav_path = str(validate_path(reference_wav_path))

        generate_kwargs: dict[str, Any] = {
            "text": text,
            "cfg_value": float(params.get("cfg_value", DEFAULT_CFG_VALUE)),
            "inference_timesteps": int(params.get("inference_timesteps", DEFAULT_INFERENCE_TIMESTEPS)),
        }
        seed = params.get("seed")
        if seed is not None:
            generate_kwargs["seed"] = int(seed)
        if use_reference and reference_wav_path:
            generate_kwargs["reference_wav_path"] = reference_wav_path

        wav = self._generate(generate_kwargs)
        if wav is None or len(wav) == 0:
            raise WorkerError(VOXCPM_INFERENCE_FAILED, "Model returned empty audio.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_wav_48k(output_path, np.asarray(wav).reshape(-1), self.sample_rate)
        duration_seconds = len(wav) / self.sample_rate
        return {
            "output_path": str(output_path),
            "sample_rate": self.sample_rate,
            "duration_seconds": duration_seconds,
            "backend": "real",
            "method": "synthesize_clone",
        }

    def _generate(self, generate_kwargs: dict[str, Any]) -> Any:
        try:
            return self.model.generate(**generate_kwargs)
        except Exception as exc:
            raise WorkerError(
                VOXCPM_INFERENCE_FAILED,
                f"VoxCPM2 inference failed: {type(exc).__name__}: {exc}",
            ) from exc


def _wav_duration_seconds(path: Path) -> float | None:
    try:
        import wave

        with wave.open(str(path), "rb") as source:
            sample_rate = source.getframerate()
            return source.getnframes() / sample_rate if sample_rate > 0 else None
    except Exception:
        return None


def _write_wav_48k(path: Path, audio: "np.ndarray", sample_rate: int) -> None:
    """Write a mono f32 numpy array to a 16-bit PCM WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype("<i2")
    byte_count = int(pcm.nbytes)
    header = b"RIFF"
    header += struct.pack("<I", 36 + byte_count)
    header += b"WAVE"
    header += b"fmt "
    header += struct.pack("<I", 16)
    header += struct.pack("<H", 1)  # PCM
    header += struct.pack("<H", 1)  # mono
    header += struct.pack("<I", sample_rate)
    header += struct.pack("<I", sample_rate * 2)
    header += struct.pack("<H", 2)
    header += struct.pack("<H", 16)
    header += b"data"
    header += struct.pack("<I", byte_count)
    path.write_bytes(header + pcm.tobytes())