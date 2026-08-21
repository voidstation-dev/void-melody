"""Mock test backend implementation for OmniVoice worker."""

from __future__ import annotations

import json
import os
import struct
import time
import wave
from pathlib import Path
from typing import Any

from errors import (
    OMNI_INVALID_PARAMS,
    OMNI_MODEL_NOT_LOADED,
    OMNI_PROMPT_INVALID,
    WorkerError,
)
from path_utils import validate_path

MAX_MOCK_DURATION_SECONDS = 60.0


class MockOmniBackend:
    """Mock backend used strictly for testing and CI.

    Never active in production unless explicitly launched with --mock flag or
    OMNIVOICE_WORKER_MODE=mock environment variable.
    """

    def __init__(self) -> None:
        self.model_loaded: bool = False
        self.model_path: str | None = None
        self.device: str = "cpu"
        self.version: str = "0.2.1"

    def ping(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"pong": True, "timestamp": time.time()}

    def runtime_info(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": "mock",
            "omnivoice_version": self.version,
            "device": self.device,
            "package_installed": True,
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "pid": os.getpid(),
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        model_path_str = params.get("model_path")
        device = params.get("device", "auto")

        if not model_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'model_path' is required")

        model_path = validate_path(model_path_str, param_name="model_path")
        self.model_loaded = True
        self.model_path = str(model_path)
        self.device = device
        return {"status": "loaded", "device": self.device, "model_path": self.model_path}

    def unload_model(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.model_loaded = False
        self.model_path = None
        return {"status": "unloaded"}

    def synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        # Optional simulated delay for timeout tests
        delay = params.get("simulate_delay_seconds")
        if delay:
            time.sleep(float(delay))

        text = params.get("text", "")
        if not text:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'text' must not be empty")

        output_path_str = params.get("output_path")
        if not output_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'output_path' is required")

        output_path = validate_path(output_path_str, param_name="output_path")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        target_duration = params.get("duration")
        raw_duration = float(target_duration) if target_duration else max(0.5, len(text) * 0.05)
        duration_seconds = min(raw_duration, MAX_MOCK_DURATION_SECONDS)

        sample_rate = 24000
        num_samples = int(sample_rate * duration_seconds)

        # Write WAV in bounded chunks (chunk_size = 4096 samples = 8192 bytes)
        chunk_size = 4096
        silent_chunk = struct.pack("<" + "h" * chunk_size, *([0] * chunk_size))

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            written = 0
            while written < num_samples:
                to_write = min(chunk_size, num_samples - written)
                if to_write == chunk_size:
                    wav_file.writeframes(silent_chunk)
                else:
                    wav_file.writeframes(struct.pack("<" + "h" * to_write, *([0] * to_write)))
                written += to_write

        return {
            "output_path": str(output_path),
            "sample_rate": sample_rate,
            "duration_seconds": duration_seconds,
        }

    def create_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path_str = params.get("audio_path")
        transcript = params.get("transcript", "")
        output_path_str = params.get("output_path")

        if not audio_path_str or not output_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameters 'audio_path' and 'output_path' are required")

        audio_path = validate_path(audio_path_str, param_name="audio_path")
        output_path = validate_path(output_path_str, param_name="output_path")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "format": "omnivoice-voice-clone-prompt",
            "version": 1,
            "audio_path": str(audio_path),
            "transcript": transcript,
            "created_at": time.time(),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        return {
            "prompt_path": str(output_path),
            "format": "omnivoice-voice-clone-prompt",
            "version": 1,
        }

    def validate_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        prompt_path_str = params.get("prompt_path")
        if not prompt_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'prompt_path' is required")

        prompt_path = validate_path(prompt_path_str, must_exist=True, param_name="prompt_path")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("format") != "omnivoice-voice-clone-prompt":
                raise ValueError("Invalid format signature")
            return {"valid": True, "prompt_path": str(prompt_path)}
        except Exception as exc:
            raise WorkerError(
                OMNI_PROMPT_INVALID,
                f"Invalid mock voice clone prompt file: {exc}",
            ) from exc

    def shutdown(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"status": "shutting_down"}
