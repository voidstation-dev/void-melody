"""Mock VoxCPM2 backend for testing and development without ML dependencies."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from backend import VoxCpmBackend
from errors import VOXCPM_INVALID_PARAMS, VOXCPM_MODEL_NOT_LOADED, WorkerError
from path_utils import validate_path_or_mock


SAMPLE_RATE = 48000


def _write_silent_wav(path: Path, duration_seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_count = int(SAMPLE_RATE * duration_seconds)
    byte_count = sample_count * 2
    data = b"\x00" * byte_count
    # WAV spec limits the RIFF chunk size to an unsigned 32-bit integer.
    max_byte_count = 0xFFFFFFFF - 36
    byte_count = min(byte_count, max_byte_count)
    header = b"RIFF"
    header += struct.pack("<I", 36 + byte_count)
    header += b"WAVE"
    header += b"fmt "
    header += struct.pack("<I", 16)
    header += struct.pack("<H", 1)  # PCM
    header += struct.pack("<H", 1)  # mono
    header += struct.pack("<I", SAMPLE_RATE)
    header += struct.pack("<I", SAMPLE_RATE * 2)
    header += struct.pack("<H", 2)
    header += struct.pack("<H", 16)
    header += b"data"
    header += struct.pack("<I", byte_count)
    path.write_bytes(header + data)


def _require_loaded(self: VoxCpmBackend, params: dict[str, Any]) -> None:
    if not getattr(self, "model_loaded", False):
        raise WorkerError(
            VOXCPM_MODEL_NOT_LOADED,
            "VoxCPM2 model is not loaded. Call load_model first.",
        )


class MockVoxCpmBackend(VoxCpmBackend):
    """Backend that produces silent 48 kHz WAV outputs for IPC plumbing tests."""

    def __init__(self) -> None:
        self.model_loaded = False
        self.device = "cpu"

    def ping(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"pong": True, "mock": True, "mode": "mock"}

    def runtime_info(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ready": True,
            "model_loaded": self.model_loaded,
            "device": self.device,
            "backend": "mock",
            "sample_rate": SAMPLE_RATE,
            "package_installed": True,
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        self.model_loaded = True
        self.device = params.get("device", "cpu")
        return {
            "status": "loaded",
            "backend": "mock",
            "device": self.device,
            "sample_rate": SAMPLE_RATE,
        }

    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.model_loaded = False
        return {"status": "unloaded", "backend": "mock"}

    def warmup(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.model_loaded:
            raise WorkerError(
                VOXCPM_MODEL_NOT_LOADED,
                "VoxCPM2 model is not loaded. Call load_model first.",
            )
        return {"status": "warm", "backend": "mock"}

    def analyze_reference(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = params.get("audio_path")
        if not audio_path:
            raise WorkerError(
                VOXCPM_INVALID_PARAMS,
                "Missing required parameter: audio_path.",
            )
        target = validate_path_or_mock(audio_path)
        duration = float(params.get("duration", 5.0) or 5.0)
        return {
            "audio_path": str(target),
            "duration_seconds": duration,
            "sample_rate": SAMPLE_RATE,
            "channels": 1,
            # Mock quality metrics; real analysis lands in Phase 3.
            "quality_score": 80.0,
            "speech_ratio": 0.85,
            "noise_level_db": -40.0,
            "clipping_ratio": 0.0,
        }

    def _synth(self, params: dict[str, Any], method: str) -> dict[str, Any]:
        if not self.model_loaded:
            raise WorkerError(
                VOXCPM_MODEL_NOT_LOADED,
                "VoxCPM2 model is not loaded. Call load_model first.",
            )
        text = params.get("text")
        output_path = params.get("output_path")
        if not text:
            raise WorkerError(VOXCPM_INVALID_PARAMS, "Missing required parameter: text.")
        if not output_path:
            raise WorkerError(
                VOXCPM_INVALID_PARAMS,
                "Missing required parameter: output_path.",
            )
        target = validate_path_or_mock(output_path)
        reference_wav_path = params.get("reference_wav_path")
        if reference_wav_path:
            validate_path_or_mock(reference_wav_path)
        delay = params.get("simulate_delay_seconds")
        if delay:
            import time

            time.sleep(float(delay))
        duration = min(max(float(params.get("duration", 1.0) or 1.0), 0.1), 60.0)
        _write_silent_wav(target, duration)
        return {
            "output_path": str(target),
            "sample_rate": SAMPLE_RATE,
            "duration_seconds": duration,
            "backend": "mock",
            "method": method,
        }

    def synthesize_clone(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._synth(params, "synthesize_clone")

    def synthesize_emotional(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._synth(params, "synthesize_emotional")

    def synthesize_ultimate(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._synth(params, "synthesize_ultimate")