"""OmniVoice isolated runtime client.

Communicates with the out-of-process OmniVoice worker via JSONL IPC on stdin/stdout.
Handles process lifecycle, serialized requests, healthchecks, timeouts, and crash recovery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OmniVoiceRuntimeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OmniSynthesisRequest:
    text: str
    output_path: str
    language: str | None = None
    instruction: str | None = None
    voice_prompt_path: str | None = None
    duration: float | None = None
    speed: float = 1.0
    normalize_text: bool = False


@dataclass(frozen=True)
class OmniSynthesisResult:
    output_path: str
    sample_rate: int
    duration_seconds: float


class OmniVoiceRuntimeClient:
    def __init__(
        self,
        *,
        worker_script_path: Path | None = None,
        python_executable: str | None = None,
        default_timeout_seconds: float = 60.0,
    ):
        if worker_script_path is None:
            # Default to apps/omnivoice-worker/worker.py relative to repo root
            current_dir = Path(__file__).resolve().parent
            repo_root = current_dir.parent.parent.parent.parent
            worker_script_path = repo_root / "apps" / "omnivoice-worker" / "worker.py"

        self.worker_script_path = Path(worker_script_path)
        self.python_executable = python_executable or sys.executable
        self.default_timeout_seconds = default_timeout_seconds

        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self._is_shutting_down = False

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def ensure_started(self) -> None:
        async with self._lock:
            if self.is_running:
                return

            self._is_shutting_down = False
            if not self.worker_script_path.is_file():
                raise OmniVoiceRuntimeError(
                    "OMNI_RUNTIME_NOT_INSTALLED",
                    f"Worker script not found at {self.worker_script_path}",
                )

            try:
                self._process = await asyncio.create_subprocess_exec(
                    self.python_executable,
                    str(self.worker_script_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self._reader_task = asyncio.create_task(self._stdout_reader_loop())
                asyncio.create_task(self._stderr_reader_loop())
                logger.info(
                    "OmniVoice worker subprocess started with PID %s",
                    self._process.pid,
                )
            except Exception as exc:
                raise OmniVoiceRuntimeError(
                    "OMNI_RUNTIME_START_FAILED",
                    f"Failed to start OmniVoice worker process: {exc}",
                ) from exc

        # Verify handshake with ping
        try:
            await self.ping(timeout_seconds=5.0)
        except Exception as exc:
            await self.shutdown()
            raise OmniVoiceRuntimeError(
                "OMNI_RUNTIME_HANDSHAKE_FAILED",
                f"OmniVoice worker handshake failed: {exc}",
            ) from exc

    async def _stdout_reader_loop(self) -> None:
        if not self._process or not self._process.stdout:
            return

        try:
            while not self._is_shutting_down:
                line = await self._process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                try:
                    data = json.loads(text)
                    req_id = data.get("id")
                    if req_id and req_id in self._pending_requests:
                        future = self._pending_requests.pop(req_id)
                        if not future.done():
                            if data.get("ok"):
                                future.set_result(data.get("result", {}))
                            else:
                                err = data.get("error", {})
                                future.set_exception(
                                    OmniVoiceRuntimeError(
                                        err.get("code", "OMNI_INFERENCE_FAILED"),
                                        err.get("message", "Unknown worker error"),
                                    )
                                )
                except Exception as parse_err:
                    logger.warning("Failed to parse worker stdout: %s", parse_err)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Error in worker stdout reader: %s", exc)
        finally:
            self._cancel_all_pending("Worker process terminated")

    async def _stderr_reader_loop(self) -> None:
        if not self._process or not self._process.stderr:
            return

        try:
            while not self._is_shutting_down:
                line = await self._process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug("[omnivoice-worker-stderr] %s", text)
        except (asyncio.CancelledError, Exception):
            pass

    def _cancel_all_pending(self, reason: str) -> None:
        for req_id, future in list(self._pending_requests.items()):
            if not future.done():
                future.set_exception(
                    OmniVoiceRuntimeError("OMNI_RUNTIME_CRASHED", reason)
                )
        self._pending_requests.clear()

    async def _call_rpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        await self.ensure_started()

        if not self.is_running or not self._process or not self._process.stdin:
            raise OmniVoiceRuntimeError(
                "OMNI_RUNTIME_CRASHED",
                "OmniVoice worker process is not running.",
            )

        req_id = str(uuid.uuid4())
        payload = {
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[req_id] = future

        timeout = timeout_seconds or self.default_timeout_seconds

        try:
            message = json.dumps(payload) + "\n"
            self._process.stdin.write(message.encode("utf-8"))
            await self._process.stdin.drain()

            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._pending_requests.pop(req_id, None)
            raise OmniVoiceRuntimeError(
                "OMNI_RUNTIME_TIMEOUT",
                f"OmniVoice RPC method '{method}' timed out after {timeout}s",
            ) from exc
        except Exception:
            self._pending_requests.pop(req_id, None)
            raise

    async def ping(self, timeout_seconds: float = 5.0) -> bool:
        result = await self._call_rpc("ping", timeout_seconds=timeout_seconds)
        return bool(result.get("pong"))

    async def get_runtime_info(self) -> dict[str, Any]:
        return await self._call_rpc("runtime_info")

    async def load_model(
        self, model_path: str, device: str = "auto"
    ) -> dict[str, Any]:
        return await self._call_rpc(
            "load_model",
            {"model_path": model_path, "device": device},
            timeout_seconds=120.0,
        )

    async def unload_model(self) -> dict[str, Any]:
        return await self._call_rpc("unload_model")

    async def synthesize(
        self,
        request: OmniSynthesisRequest,
        timeout_seconds: float | None = None,
    ) -> OmniSynthesisResult:
        result = await self._call_rpc(
            "synthesize",
            asdict(request),
            timeout_seconds=timeout_seconds,
        )
        return OmniSynthesisResult(
            output_path=result["output_path"],
            sample_rate=result["sample_rate"],
            duration_seconds=result["duration_seconds"],
        )

    async def create_voice_prompt(
        self,
        *,
        audio_path: str,
        transcript: str,
        output_path: str,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        return await self._call_rpc(
            "create_voice_prompt",
            {
                "audio_path": audio_path,
                "transcript": transcript,
                "output_path": output_path,
            },
            timeout_seconds=timeout_seconds,
        )

    async def shutdown(self) -> None:
        self._is_shutting_down = True
        if self._process and self.is_running:
            try:
                # Send graceful shutdown RPC
                if self._process.stdin:
                    req_id = "shutdown-req"
                    payload = {"id": req_id, "method": "shutdown", "params": {}}
                    self._process.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
                    await self._process.stdin.drain()
                await asyncio.wait_for(self._process.wait(), timeout=3.0)
            except Exception:
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
                await self._process.wait()

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()

        self._process = None
        self._cancel_all_pending("Worker process shut down")
