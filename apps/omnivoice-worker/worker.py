"""OmniVoice isolated runtime worker entrypoint.

Communicates with the parent process strictly via JSONL on stdin/stdout.
Standard error (stderr) is used for all diagnostics/logging.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from backend import OmniBackend
from errors import (
    OMNI_INVALID_PARAMS,
    OMNI_INVALID_REQUEST,
    OMNI_METHOD_NOT_FOUND,
    OMNI_WORKER_INTERNAL_ERROR,
    WorkerError,
)
from mock_backend import MockOmniBackend
from real_backend import RealOmniBackend


def log_debug(message: str) -> None:
    sys.stderr.write(f"[omnivoice-worker] {message}\n")
    sys.stderr.flush()


class OmniVoiceWorker:
    def __init__(self, backend: OmniBackend) -> None:
        self.backend = backend
        self.running: bool = True

    def dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "ping": self.backend.ping,
            "runtime_info": self.backend.runtime_info,
            "load_model": self.backend.load_model,
            "unload_model": self.backend.unload_model,
            "synthesize": self.backend.synthesize,
            "create_voice_prompt": self.backend.create_voice_prompt,
            "validate_voice_prompt": self.backend.validate_voice_prompt,
            "shutdown": self.backend.shutdown,
        }
        handler = handlers.get(method)
        if not handler:
            raise WorkerError(OMNI_METHOD_NOT_FOUND, f"Unknown RPC method: '{method}'")
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
                try:
                    request = json.loads(line)
                except Exception as json_err:
                    raise WorkerError(
                        OMNI_INVALID_REQUEST,
                        f"Malformed JSON request: {json_err}",
                    ) from json_err

                if not isinstance(request, dict):
                    raise WorkerError(OMNI_INVALID_REQUEST, "Request must be a JSON object")

                req_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})

                if not req_id or not isinstance(req_id, str):
                    raise WorkerError(OMNI_INVALID_REQUEST, "Field 'id' (string) is required")

                if not method or not isinstance(method, str):
                    raise WorkerError(OMNI_INVALID_REQUEST, "Field 'method' (string) is required")

                if not isinstance(params, dict):
                    raise WorkerError(OMNI_INVALID_PARAMS, "Field 'params' must be a JSON object")

                result = self.dispatch(method, params)
                response = {"id": req_id, "ok": True, "result": result}

                if method == "shutdown":
                    self.running = False
            except WorkerError as exc:
                response = {
                    "id": req_id,
                    "ok": False,
                    "error": exc.to_dict(),
                }
            except Exception as exc:
                log_debug(f"Unhandled worker error on request {req_id}: {exc}")
                response = {
                    "id": req_id,
                    "ok": False,
                    "error": {
                        "code": OMNI_WORKER_INTERNAL_ERROR,
                        "message": str(exc),
                    },
                }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

            if not self.running:
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniVoice isolated runtime worker")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (strictly for automated tests/CI)",
    )
    args = parser.parse_args()

    # Determine mode: explicit CLI flag or explicit env variable
    is_mock = args.mock or os.environ.get("OMNIVOICE_WORKER_MODE") == "mock"

    if is_mock:
        os.environ["OMNIVOICE_WORKER_MODE"] = "mock"
        log_debug("Starting worker with MockOmniBackend")
        backend: OmniBackend = MockOmniBackend()
    else:
        log_debug("Starting worker with RealOmniBackend")
        backend = RealOmniBackend()

    worker = OmniVoiceWorker(backend)
    worker.run()


if __name__ == "__main__":
    main()
