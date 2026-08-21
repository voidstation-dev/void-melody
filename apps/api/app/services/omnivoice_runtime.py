"""OmniVoice isolated runtime client.

Communicates with the out-of-process OmniVoice worker via JSONL IPC on stdin/stdout.
Handles process generation isolation, serialized requests, healthchecks, timeouts,
and worker crash recovery.
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
    simulate_delay_seconds: float | None = None


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
        mock_mode: bool = False,
    ):
        if worker_script_path is None:
            # Default to apps/omnivoice-worker/worker.py relative to repo root
            current_dir = Path(__file__).resolve().parent
            repo_root = current_dir.parent.parent.parent.parent
            worker_script_path = repo_root / "apps" / "omnivoice-worker" / "worker.py"

        self.worker_script_path = Path(worker_script_path)
        self.python_executable = python_executable or sys.executable
        self.default_timeout_seconds = default_timeout_seconds
        self.mock_mode = mock_mode

        self._process: asyncio.subprocess.Process | None = None
        self._generation: str | None = None
        self._stdout_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._pending_requests: dict[str, tuple[asyncio.Future[dict[str, Any]], str]] = {}
        self._lock = asyncio.Lock()
        self._is_shutting_down = False

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    @property
    def generation(self) -> str | None:
        return self._generation

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

            gen = uuid.uuid4().hex
            args = [self.python_executable, str(self.worker_script_path)]
            if self.mock_mode:
                args.append("--mock")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self._process = proc
                self._generation = gen
                self._stdout_task = asyncio.create_task(self._stdout_reader_loop(proc, gen))
                self._stderr_task = asyncio.create_task(self._stderr_reader_loop(proc, gen))
                logger.info(
                    "OmniVoice worker subprocess started (PID=%s, gen=%s, mock=%s)",
                    proc.pid,
                    gen,
                    self.mock_mode,
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
            if isinstance(exc, OmniVoiceRuntimeError):
                raise
            raise OmniVoiceRuntimeError(
                "OMNI_RUNTIME_HANDSHAKE_FAILED",
                f"OmniVoice worker handshake failed: {exc}",
            ) from exc

    async def _stdout_reader_loop(self, proc: asyncio.subprocess.Process, gen: str) -> None:
        if not proc.stdout:
            return

        try:
            while not self._is_shutting_down and proc.returncode is None:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                try:
                    data = json.loads(text)
                    req_id = data.get("id")
                    if req_id and req_id in self._pending_requests:
                        future, req_gen = self._pending_requests.pop(req_id)
                        if req_gen == gen and not future.done():
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
                    logger.warning("Failed to parse worker stdout line: %s", parse_err)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Error in worker stdout reader: %s", exc)
        finally:
            self._cancel_generation_pending(gen, "Worker process terminated")

    async def _stderr_reader_loop(self, proc: asyncio.subprocess.Process, gen: str) -> None:
        if not proc.stderr:
            return

        try:
            while not self._is_shutting_down and proc.returncode is None:
                line = await proc.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug("[omnivoice-worker-stderr:%s] %s", gen[:8], text)
        except (asyncio.CancelledError, Exception):
            pass

    def _cancel_generation_pending(self, gen: str, reason: str) -> None:
        for req_id, (future, req_gen) in list(self._pending_requests.items()):
            if req_gen == gen:
                self._pending_requests.pop(req_id, None)
                if not future.done():
                    future.set_exception(
                        OmniVoiceRuntimeError("OMNI_RUNTIME_CRASHED", reason)
                    )

    async def _call_rpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        await self.ensure_started()

        proc = self._process
        gen = self._generation
        if not self.is_running or not proc or not proc.stdin or not gen:
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
        self._pending_requests[req_id] = (future, gen)

        timeout = timeout_seconds or self.default_timeout_seconds

        try:
            message = json.dumps(payload) + "\n"
            proc.stdin.write(message.encode("utf-8"))
            await proc.stdin.drain()

            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._pending_requests.pop(req_id, None)
            logger.warning(
                "OmniVoice RPC '%s' timed out after %ss on generation %s. Terminating poisoned worker.",
                method,
                timeout,
                gen,
            )
            # Invalidate and kill the stuck synchronous worker process
            await self._kill_generation(proc, gen)
            raise OmniVoiceRuntimeError(
                "OMNI_RUNTIME_TIMEOUT",
                f"OmniVoice RPC method '{method}' timed out after {timeout}s",
            ) from exc
        except Exception:
            self._pending_requests.pop(req_id, None)
            raise

    async def _kill_generation(self, proc: asyncio.subprocess.Process, gen: str) -> None:
        """Immediately terminate a poisoned or crashed worker generation."""
        try:
            proc.kill()
        except ProcessLookupError:
            pass

        self._cancel_generation_pending(gen, "Worker process terminated due to timeout")
        if self._process == proc:
            self._process = None
            self._generation = None

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
        params = {k: v for k, v in asdict(request).items() if v is not None}
        result = await self._call_rpc(
            "synthesize",
            params,
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

    async def validate_voice_prompt(
        self,
        prompt_path: str,
        timeout_seconds: float = 10.0,
    ) -> dict[str, Any]:
        return await self._call_rpc(
            "validate_voice_prompt",
            {"prompt_path": prompt_path},
            timeout_seconds=timeout_seconds,
        )

    async def shutdown(self) -> None:
        self._is_shutting_down = True
        proc = self._process
        gen = self._generation

        if proc and self.is_running:
            try:
                if proc.stdin:
                    req_id = "shutdown-req"
                    payload = {"id": req_id, "method": "shutdown", "params": {}}
                    proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
                    await proc.stdin.drain()
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()

        # Cleanly cancel and gather reader tasks
        tasks = [t for t in (self._stdout_task, self._stderr_task) if t and not t.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if gen:
            self._cancel_generation_pending(gen, "Worker process shut down")

        self._process = None
        self._generation = None
        self._stdout_task = None
        self._stderr_task = None
