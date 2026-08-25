"""Melody Speech Worker — standalone JSONL-over-stdin/stdout RPC.

Methods:
  probe              → runtime/protocol/device info
  detect_speech      → Silero VAD speech timeline for a local audio path
  transcribe         → faster-whisper transcription of a local audio path
  transcribe_segment → transcribe a bounded segment [start,end] seconds
  unload             → release loaded models

Audio is passed by local filesystem path, never as binary JSON.

This scaffold ships with a mock backend so the protocol can be tested
without heavy ML dependencies. The real backend (real_backend.py)
wraps faster-whisper + Silero VAD and is imported lazily only when the
runtime pack is installed.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Protocol

logger = logging.getLogger(__name__)
PROTOCOL_VERSION = 1
RUNTIME_VERSION = "0.1.0"


class SpeechBackend(Protocol):
    def probe(self) -> dict[str, Any]: ...
    def detect_speech(self, audio_path: str) -> dict[str, Any]: ...
    def transcribe(self, audio_path: str, *, language: str | None = None) -> dict[str, Any]: ...
    def transcribe_segment(
        self, audio_path: str, *, start: float, end: float, language: str | None = None
    ) -> dict[str, Any]: ...
    def unload(self) -> None: ...


class MockSpeechBackend:
    """No-op backend for protocol testing without ML deps."""

    def probe(self) -> dict[str, Any]:
        return {
            "runtimeVersion": RUNTIME_VERSION,
            "protocolVersion": PROTOCOL_VERSION,
            "device": "cpu",
            "backend": "mock",
            "vadReady": True,
            "whisperReady": False,
        }

    def detect_speech(self, audio_path: str) -> dict[str, Any]:
        return {
            "audioPath": audio_path,
            "regions": [],
            "speechRatio": 0.0,
            "continuousSpeechScore": 0.0,
        }

    def transcribe(self, audio_path: str, *, language: str | None = None) -> dict[str, Any]:
        return {"audioPath": audio_path, "text": "", "language": language or "vi", "segments": []}

    def transcribe_segment(
        self, audio_path: str, *, start: float, end: float, language: str | None = None
    ) -> dict[str, Any]:
        return {
            "audioPath": audio_path,
            "start": start,
            "end": end,
            "text": "",
            "language": language or "vi",
        }

    def unload(self) -> None:
        pass


def _get_backend(use_mock: bool = True) -> SpeechBackend:
    if use_mock:
        return MockSpeechBackend()
    from backend.real_backend import RealSpeechBackend  # type: ignore[import-not-found]

    return RealSpeechBackend()


def _handle_request(backend: SpeechBackend, req: dict[str, Any]) -> dict[str, Any]:
    method = req.get("method", "")
    params = req.get("params", {})
    req_id = req.get("id", "")

    try:
        if method == "probe":
            result = backend.probe()
        elif method == "detect_speech":
            result = backend.detect_speech(params["audioPath"])
        elif method == "transcribe":
            result = backend.transcribe(
                params["audioPath"], language=params.get("language")
            )
        elif method == "transcribe_segment":
            result = backend.transcribe_segment(
                params["audioPath"],
                start=params["start"],
                end=params["end"],
                language=params.get("language"),
            )
        elif method == "unload":
            backend.unload()
            result = {"unloaded": True}
        elif method == "shutdown":
            result = {"shutdown": True}
        else:
            return {
                "id": req_id,
                "ok": False,
                "error": {"code": "UNKNOWN_METHOD", "message": f"Unknown method: {method}"},
            }
        return {"id": req_id, "ok": True, "result": result}
    except KeyError as exc:
        return {
            "id": req_id,
            "ok": False,
            "error": {"code": "MISSING_PARAM", "message": f"Missing parameter: {exc}"},
        }
    except Exception as exc:
        logger.exception("speech worker error")
        return {
            "id": req_id,
            "ok": False,
            "error": {"code": "WORKER_ERROR", "message": str(exc)},
        }


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    use_mock = "--mock" in sys.argv or "--real" not in sys.argv
    backend = _get_backend(use_mock=use_mock)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            resp = {
                "id": "",
                "ok": False,
                "error": {"code": "BAD_JSON", "message": "Invalid JSON line"},
            }
        else:
            resp = _handle_request(backend, req)
            if resp.get("result", {}).get("shutdown"):
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
                break
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()