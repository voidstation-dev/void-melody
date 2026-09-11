#!/usr/bin/env python3
"""VoxCPM2 out-of-process worker.

Reads JSONL requests from stdin and writes JSONL responses to stdout.
Supports a lightweight mock backend (no ML dependencies); the real backend
defers torch/voxcpm imports until load_model (Phase 4).

Owns VoxCPM2 semantics only: no fallback, provider_id = "voxcpm2".
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from backend import VoxCpmBackend
from errors import VOXCPM_INVALID_PARAMS, VOXCPM_METHOD_NOT_FOUND, WorkerError

logger = logging.getLogger(__name__)


def _load_backend(mock: bool) -> VoxCpmBackend:
    if mock or os.environ.get("VOXCPM_WORKER_MODE") == "mock":
        from mock_backend import MockVoxCpmBackend

        return MockVoxCpmBackend()
    from real_backend import RealVoxCpmBackend

    return RealVoxCpmBackend()


class VoxCpmWorker:
    """JSONL request dispatcher for the VoxCPM2 worker process."""

    def __init__(self, backend: VoxCpmBackend) -> None:
        self.backend = backend

    def run(self) -> None:
        """Read JSONL from stdin and emit JSONL on stdout until EOF."""
        self._stop = False
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                self._respond("", error={"code": "INVALID_JSON", "message": str(exc)})
                continue

            if getattr(self, "_stop", False):
                break

            req_id = req.get("id", "")
            method = req.get("method", "")
            params = req.get("params", {})
            self._dispatch(req_id, method, params)

    def _dispatch(self, req_id: str, method: str, params: Any) -> None:
        if not isinstance(params, dict):
            self._respond(
                req_id,
                error={
                    "code": VOXCPM_INVALID_PARAMS,
                    "message": "Request params must be an object.",
                },
            )
            return

        if method == "shutdown":
            self._respond(req_id, result={"status": "shutting_down"})
            # Closing sys.stdin mid-iteration raises ValueError on Windows
            # (and taints the iterator in CPython). Ask run() to stop instead.
            self._stop = True
            return

        handler = getattr(self.backend, method, None)
        if handler is None:
            self._respond(
                req_id,
                error={
                    "code": VOXCPM_METHOD_NOT_FOUND,
                    "message": f"Unknown method: {method}",
                },
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
                error={"code": "VOXCPM_WORKER_ERROR", "message": f"{type(exc).__name__}: {exc}"},
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
    logger.info("VoxCPM2 worker started (mock=%s)", args.mock)
    worker = VoxCpmWorker(backend)
    worker.run()


if __name__ == "__main__":
    main()