"""Mock OmniVoice backend for testing and development without ML dependencies."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from backend import OmniBackend
from errors import OMNI_INVALID_PARAMS, OMNI_PROMPT_INVALID, WorkerError
from path_utils import validate_path_or_mock


SAMPLE_RATE = 24000


def _write_silent_wav(path: Path, duration_seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_count = int(SAMPLE_RATE * duration_seconds)
    byte_count = sample_count * 2
    data = b"\x00" * byte_count
    # WAV spec limits the RIFF chunk size to an unsigned 32-bit integer.
    # Cap duration to keep the total file size within that bound.
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


class MockOmniBackend(OmniBackend):
    """Backend that produces silent WAV outputs for testing IPC plumbing."""

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
            "mock": True,
            "mode": "mock",
            "package_installed": True,
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        self.model_loaded = True
        self.device = params.get("device", "cpu")
        return {"status": "loaded", "mock": True, "device": self.device, "mode": "mock"}

    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.model_loaded = False
        return {"status": "unloaded", "mock": True, "mode": "mock"}

    def synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        output_path = params.get("output_path")
        if not output_path:
            raise WorkerError(
                OMNI_INVALID_PARAMS,
                "Missing required parameter: output_path.",
            )
        target = validate_path_or_mock(output_path)
        duration = float(params.get("duration", 1.0) or 1.0)
        speed = float(params.get("speed", 1.0) or 1.0)
        delay = params.get("simulate_delay_seconds")
        if delay:
            import time

            time.sleep(float(delay))
        effective_duration = min(duration / max(speed, 0.1), 60.0)
        _write_silent_wav(target, effective_duration)
        return {
            "output_path": str(target),
            "sample_rate": SAMPLE_RATE,
            "duration_seconds": effective_duration,
        }

    def create_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = params.get("audio_path")
        output_path = params.get("output_path")
        if not audio_path or not output_path:
            raise WorkerError(
                OMNI_INVALID_PARAMS,
                "Missing required parameter: audio_path or output_path.",
            )
        target = validate_path_or_mock(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"OMNIVOICE_VOICE_CLONE_PROMPT_V1")
        return {
            "output_path": str(target),
            "format_version": "omnivoice-voice-clone-prompt",
            "format": "omnivoice-voice-clone-prompt",
            "sample_rate": SAMPLE_RATE,
            "prompt_path": str(target),
        }

    def validate_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        prompt_path = params.get("prompt_path")
        if not prompt_path:
            raise WorkerError(
                OMNI_INVALID_PARAMS,
                "Missing required parameter: prompt_path.",
            )
        target = validate_path_or_mock(prompt_path)
        data = target.read_bytes()
        if data != b"OMNIVOICE_VOICE_CLONE_PROMPT_V1":
            raise WorkerError(OMNI_PROMPT_INVALID, "Invalid prompt artifact.")
        return {"valid": True}
