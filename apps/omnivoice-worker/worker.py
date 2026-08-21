"""OmniVoice isolated runtime worker.

Communicates with the parent process (Melody API) strictly via newline-delimited
JSON (JSONL) on stdin/stdout. Standard error (stderr) is used for all logging.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def log_debug(message: str) -> None:
    sys.stderr.write(f"[omnivoice-worker] {message}\n")
    sys.stderr.flush()


class OmniVoiceWorker:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.model_path: str | None = None
        self.device: str = "cpu"
        self.version: str = "0.2.1"
        self.running: bool = True

    def handle_ping(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"pong": True, "timestamp": time.time()}

    def handle_runtime_info(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {
            "omnivoice_version": self.version,
            "device": self.device,
            "model_loaded": self.model is not None,
            "model_path": self.model_path,
            "pid": os.getpid(),
        }

    def handle_load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        model_path = params.get("model_path")
        device = params.get("device", "auto")
        self.device = device
        self.model_path = model_path
        
        # If running in mock/test environment without real omnivoice package
        try:
            # When real omnivoice is installed:
            # from omnivoice import OmniVoice
            # self.model = OmniVoice.from_pretrained(model_path, device=device)
            self.model = {"mock_model": True, "path": model_path, "device": device}
        except Exception as exc:
            raise RuntimeError(f"Failed to load OmniVoice model: {exc}") from exc

        log_debug(f"Model loaded on device {self.device}")
        return {"status": "loaded", "device": self.device, "model_path": model_path}

    def handle_unload_model(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.model = None
        self.model_path = None
        log_debug("Model unloaded")
        return {"status": "unloaded"}

    def handle_synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        text = params.get("text", "")
        output_path = params.get("output_path")
        target_duration = params.get("duration")
        sample_rate = 24000

        if not output_path:
            raise ValueError("output_path is required")

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Generate output audio file (mock WAV or real inference)
        # Create a valid minimal WAV file header if no real engine
        duration_seconds = float(target_duration) if target_duration else max(0.5, len(text) * 0.08)
        num_samples = int(sample_rate * duration_seconds)

        import wave
        import struct

        with wave.open(str(out_file), "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            # Write silence / basic tone PCM frames
            data = struct.pack("<" + "h" * num_samples, *([0] * num_samples))
            wav_file.writeframes(data)

        log_debug(f"Synthesized {duration_seconds:.2f}s audio to {output_path}")
        return {
            "output_path": str(out_file),
            "sample_rate": sample_rate,
            "duration_seconds": duration_seconds,
        }

    def handle_create_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = params.get("audio_path")
        transcript = params.get("transcript", "")
        output_path = params.get("output_path")

        if not audio_path or not output_path:
            raise ValueError("audio_path and output_path are required")

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # In real OmniVoice:
        # prompt = model.create_voice_clone_prompt(ref_audio=audio_path, ref_text=transcript)
        # prompt.save(output_path)
        # For mock/file format:
        payload = {
            "format": "omnivoice-voice-clone-prompt",
            "version": 1,
            "transcript": transcript,
            "created_at": time.time(),
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        log_debug(f"Created voice clone prompt artifact at {output_path}")
        return {
            "prompt_path": str(out_file),
            "format": "omnivoice-voice-clone-prompt",
            "version": 1,
        }

    def handle_shutdown(self, _params: dict[str, Any]) -> dict[str, Any]:
        self.running = False
        log_debug("Worker shutting down")
        return {"status": "shutting_down"}

    def dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "ping": self.handle_ping,
            "runtime_info": self.handle_runtime_info,
            "load_model": self.handle_load_model,
            "unload_model": self.handle_unload_model,
            "synthesize": self.handle_synthesize,
            "create_voice_prompt": self.handle_create_voice_prompt,
            "shutdown": self.handle_shutdown,
        }
        handler = handlers.get(method)
        if not handler:
            raise ValueError(f"Unknown method: {method}")
        return handler(params)

    def run(self) -> None:
        log_debug(f"Worker process started with PID {os.getpid()}")
        while self.running:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            req_id = None
            try:
                request = json.loads(line)
                req_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})

                if not req_id or not method:
                    raise ValueError("Request must contain 'id' and 'method'")

                result = self.dispatch(method, params)
                response = {"id": req_id, "ok": True, "result": result}
            except Exception as exc:
                log_debug(f"Error handling request {req_id}: {exc}")
                response = {
                    "id": req_id,
                    "ok": False,
                    "error": {
                        "code": type(exc).__name__,
                        "message": str(exc),
                    },
                }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

            if not self.running:
                break


if __name__ == "__main__":
    worker = OmniVoiceWorker()
    worker.run()
