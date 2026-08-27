"""Real OmniVoice backend stub.

This file provides the worker-side backend contract. The actual torch/omnivoice
imports are deferred until load_model so the file is safe to import in tests.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import numpy as np

from backend import OmniBackend
from errors import OMNI_INFERENCE_FAILED, OMNI_PACKAGE_NOT_INSTALLED, WorkerError
from path_utils import validate_path


class RealOmniBackend(OmniBackend):
    """Backend that will eventually delegate to the real OmniVoice model."""

    def __init__(self) -> None:
        self.model: Any | None = None
        self.device: str = "cpu"
        self._import_error: Exception | None = None
        try:
            import omnivoice  # noqa: F401
        except Exception as exc:
            self._import_error = exc

    # ---- contract methods ----

    def ping(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"pong": True}

    def runtime_info(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ready": self.model is not None,
            "model_loaded": self.model is not None,
            "device": self.device,
            "real": True,
            "mode": "real",
            "package_installed": self._import_error is None,
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._import_error is not None:
            raise WorkerError(
                OMNI_PACKAGE_NOT_INSTALLED,
                f"Failed to import omnivoice: {self._import_error}",
            )

        model_path = validate_path(params["model_path"])
        device = params.get("device", "cpu")

        # Defer real import to first load.
        from omnivoice import OmniVoice  # type: ignore[import-not-found]

        self.model = OmniVoice.from_pretrained(str(model_path), device_map=device)
        self.device = device
        return {"status": "loaded", "device": device}

    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.model = None
        return {"unloaded": True}

    def synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.model is None:
            raise WorkerError(
                "OMNI_MODEL_NOT_LOADED",
                "Model is not loaded.",
            )

        output_path = validate_path(params["output_path"])
        text = params["text"]

        audios = self.model.generate(texts=[text])
        if not audios:
            raise WorkerError(
                OMNI_INFERENCE_FAILED,
                "Model returned empty audio list.",
            )

        audio = audios[0]
        sample_rate = int(getattr(self.model, "sampling_rate", 24000))
        duration_seconds = float(len(audio)) / sample_rate

        _write_wav(output_path, audio, sample_rate)
        return {
            "output_path": str(output_path),
            "sample_rate": sample_rate,
            "duration_seconds": duration_seconds,
        }

    def create_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = validate_path(params["audio_path"])
        output_path = validate_path(params["output_path"])

        if self.model is None:
            # Stub: accept the reference audio and write a marker artifact.
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_path.read_bytes())
            return {
                "output_path": str(output_path),
                "format_version": "omnivoice-voice-clone-prompt",
                "sample_rate": 24000,
            }

        prompt = self.model.create_voice_clone_prompt(
            ref_audio=str(audio_path),
            ref_text=params.get("transcript", ""),
        )
        output_path.write_bytes(prompt)
        return {
            "output_path": str(output_path),
            "format_version": "omnivoice-voice-clone-prompt",
            "sample_rate": 24000,
        }

    def validate_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        prompt_path = validate_path(params["prompt_path"])
        if not prompt_path.is_file():
            raise WorkerError("OMNI_PROMPT_INVALID", "Prompt artifact not found.")
        # Real validation would inspect the prompt blob.
        return {"valid": True}


def _write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    """Write a mono f32 numpy array to a WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Convert to int16 PCM
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)
    byte_count = pcm.nbytes
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
