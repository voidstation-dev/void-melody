#!/usr/bin/env python3
"""OmniVoice out-of-process worker.

Reads JSONL requests from stdin and writes JSONL responses to stdout.
Supports both a lightweight mock backend (no ML dependencies) and a real
backend that defers torch/omnivoice imports until load_model.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from backend import OmniBackend
from errors import OMNI_INVALID_PARAMS, WorkerError

logger = logging.getLogger(__name__)


def _load_backend(mock: bool) -> OmniBackend:
    if mock or os.environ.get("OMNIVOICE_WORKER_MODE") == "mock":
        from mock_backend import MockOmniBackend

        return MockOmniBackend()
    from real_backend import RealOmniBackend

    return RealOmniBackend()


class OmniVoiceWorker:
    """JSONL request dispatcher for the OmniVoice worker process."""

    def __init__(self, backend: OmniBackend) -> None:
        self.backend = backend

    def run(self) -> None:
        """Read JSONL from stdin and emit JSONL on stdout until EOF."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                self._respond("", error={"code": "INVALID_JSON", "message": str(exc)})
                continue

            req_id = req.get("id", "")
            method = req.get("method", "")
            params = req.get("params", {})
            self._dispatch(req_id, method, params)

    def _dispatch(self, req_id: str, method: str, params: Any) -> None:
        if not isinstance(params, dict):
            self._respond(
                req_id,
                error={
                    "code": OMNI_INVALID_PARAMS,
                    "message": "Request params must be an object.",
                },
            )
            return

        handler = getattr(self.backend, method, None)
        if handler is None:
            self._respond(
                req_id,
                error={"code": "OMNI_METHOD_NOT_FOUND", "message": f"Unknown method: {method}"},
            )
            return

        # Synchronous workers use time.sleep for simulated delays.
        delay = params.get("simulate_delay_seconds")
        if delay:
            import time

            time.sleep(float(delay))

        try:
            result = handler(params)
            self._respond(req_id, result=result)
        except WorkerError as exc:
            self._respond(req_id, error={"code": exc.code, "message": exc.message})
        except Exception as exc:
            logger.exception("Request failed: %s", method)
            self._respond(
                req_id,
                error={"code": "WORKER_ERROR", "message": f"{type(exc).__name__}: {exc}"},
            )

    def _respond(self, req_id: str, result: dict | None = None, error: dict | None = None) -> None:
        payload: dict = {"id": req_id}
        if error is not None:
            payload["ok"] = False
            payload["error"] = error
        else:
            payload["ok"] = True
            payload["result"] = result or {}
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    backend = _load_backend(mock=args.mock)
    logger.info("OmniVoice worker started (mock=%s)", args.mock)
    worker = OmniVoiceWorker(backend)
    worker.run()


if __name__ == "__main__":
    main()
