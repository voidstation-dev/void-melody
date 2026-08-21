"""Real production OmniVoice backend implementation."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

from errors import (
    OMNI_INFERENCE_FAILED,
    OMNI_INVALID_PARAMS,
    OMNI_MODEL_LOAD_FAILED,
    OMNI_MODEL_NOT_INSTALLED,
    OMNI_MODEL_NOT_LOADED,
    OMNI_PACKAGE_NOT_INSTALLED,
    OMNI_PROMPT_CREATE_FAILED,
    OMNI_PROMPT_INVALID,
    WorkerError,
)
from path_utils import validate_path


class RealOmniBackend:
    """Production backend executing real OmniVoice inference.

    Never falls back to mock behavior. If dependencies or models are missing,
    it raises explicit WorkerError with stable error codes.
    """

    def __init__(self) -> None:
        self.model: Any | None = None
        self.model_path: str | None = None
        self.device: str = "cpu"
        self.version: str = "0.2.1"
        self._check_package_availability()

    def _check_package_availability(self) -> None:
        try:
            import omnivoice  # noqa: F401
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError as exc:
            # Package not installed in the current environment
            self._import_error = str(exc)
        else:
            self._import_error = None

    def _ensure_package_installed(self) -> None:
        if self._import_error:
            raise WorkerError(
                OMNI_PACKAGE_NOT_INSTALLED,
                f"OmniVoice runtime dependencies not installed in worker environment: {self._import_error}",
            )

    def ping(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"pong": True, "timestamp": time.time()}

    def runtime_info(self, _params: dict[str, Any]) -> dict[str, Any]:
        self._check_package_availability()
        return {
            "mode": "real",
            "omnivoice_version": self.version,
            "device": self.device,
            "package_installed": self._import_error is None,
            "model_loaded": self.model is not None,
            "model_path": self.model_path,
            "pid": os.getpid(),
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_package_installed()
        model_path_str = params.get("model_path")
        device = params.get("device", "auto")

        if not model_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'model_path' is required")

        model_path = validate_path(model_path_str, param_name="model_path")
        if not model_path.exists():
            raise WorkerError(
                OMNI_MODEL_NOT_INSTALLED,
                f"OmniVoice model directory not found at {model_path}",
            )

        try:
            from omnivoice import OmniVoice

            self.model = OmniVoice.from_pretrained(str(model_path), device_map=device)
            self.model_path = str(model_path)
            self.device = str(getattr(self.model, "device", device))
            return {"status": "loaded", "device": self.device, "model_path": self.model_path}
        except Exception as exc:
            raise WorkerError(
                OMNI_MODEL_LOAD_FAILED,
                f"Failed to load OmniVoice model from {model_path}: {exc}",
            ) from exc

    def unload_model(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.model = None
        self.model_path = None
        return {"status": "unloaded"}

    def synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_package_installed()
        if self.model is None:
            raise WorkerError(OMNI_MODEL_NOT_LOADED, "OmniVoice model is not loaded")

        text = params.get("text", "")
        if not text:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'text' must not be empty")

        output_path_str = params.get("output_path")
        if not output_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'output_path' is required")

        output_path = validate_path(output_path_str, param_name="output_path")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        language = params.get("language")
        instruction = params.get("instruction")
        voice_prompt_path_str = params.get("voice_prompt_path")
        duration = params.get("duration")
        speed = params.get("speed", 1.0)
        normalize_text = params.get("normalize_text", False)

        prompt = None
        if voice_prompt_path_str:
            prompt_path = validate_path(voice_prompt_path_str, must_exist=True, param_name="voice_prompt_path")
            try:
                from omnivoice import VoiceClonePrompt

                prompt = VoiceClonePrompt.load(str(prompt_path))
            except Exception as exc:
                raise WorkerError(
                    OMNI_PROMPT_INVALID,
                    f"Failed to load VoiceClonePrompt from {prompt_path}: {exc}",
                ) from exc

        try:
            audios = self.model.generate(
                text=text,
                language=language,
                voice_clone_prompt=prompt,
                instruct=instruction,
                duration=duration,
                speed=speed,
                normalize_text=normalize_text,
            )
            if not audios:
                raise WorkerError(
                    OMNI_INFERENCE_FAILED,
                    "OmniVoice returned no audio.",
                )

            wav = audios[0]
            sample_rate = int(getattr(self.model, "sampling_rate", 24000))

            import soundfile as sf

            sf.write(str(output_path), wav, sample_rate)
            duration_seconds = len(wav) / float(sample_rate)

            return {
                "output_path": str(output_path),
                "sample_rate": sample_rate,
                "duration_seconds": duration_seconds,
            }
        except WorkerError:
            raise
        except Exception as exc:
            raise WorkerError(
                OMNI_INFERENCE_FAILED,
                f"OmniVoice synthesis failed: {exc}",
            ) from exc

    def create_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_package_installed()
        if self.model is None:
            raise WorkerError(OMNI_MODEL_NOT_LOADED, "OmniVoice model is not loaded")

        audio_path_str = params.get("audio_path")
        transcript = params.get("transcript", "")
        output_path_str = params.get("output_path")

        if not audio_path_str or not output_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameters 'audio_path' and 'output_path' are required")

        audio_path = validate_path(audio_path_str, must_exist=True, param_name="audio_path")
        output_path = validate_path(output_path_str, param_name="output_path")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            prompt = self.model.create_voice_clone_prompt(
                ref_audio=str(audio_path),
                ref_text=transcript,
            )
            prompt.save(str(output_path))

            return {
                "prompt_path": str(output_path),
                "format": "omnivoice-voice-clone-prompt",
                "version": 1,
            }
        except Exception as exc:
            raise WorkerError(
                OMNI_PROMPT_CREATE_FAILED,
                f"Failed to create VoiceClonePrompt from {audio_path}: {exc}",
            ) from exc

    def validate_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_package_installed()
        prompt_path_str = params.get("prompt_path")
        if not prompt_path_str:
            raise WorkerError(OMNI_INVALID_PARAMS, "Parameter 'prompt_path' is required")

        prompt_path = validate_path(prompt_path_str, must_exist=True, param_name="prompt_path")
        try:
            from omnivoice import VoiceClonePrompt

            _ = VoiceClonePrompt.load(str(prompt_path))
            return {"valid": True, "prompt_path": str(prompt_path)}
        except Exception as exc:
            raise WorkerError(
                OMNI_PROMPT_INVALID,
                f"Invalid VoiceClonePrompt at {prompt_path}: {exc}",
            ) from exc

    def shutdown(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"status": "shutting_down"}
