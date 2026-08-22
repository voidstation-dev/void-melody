"""Isolated queue for Emotional Script renders.

The queue deliberately has no relationship with ``TTSQueueManager`` or
``tts_jobs``. It provides one bounded worker in the MVP and can yield between
render units in the service layer.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class ScriptRenderQueueManager:
    def __init__(self, executor: Callable[[str], Awaitable[None]] | None = None) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._executor = executor
        self._worker: asyncio.Task[None] | None = None
        self.accepting_jobs = False
        self.enqueued_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self.accepting_jobs = True
        self._worker = asyncio.create_task(self._run(), name="script-render-queue")

    async def stop(self) -> None:
        self.accepting_jobs = False
        if self._worker:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None
        self.enqueued_ids.clear()
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()

    async def enqueue(self, render_id: str) -> bool:
        if not self.accepting_jobs:
            raise RuntimeError("Script render queue is not accepting jobs")
        async with self._lock:
            if render_id in self.enqueued_ids:
                return False
            self.enqueued_ids.add(render_id)
        await self._queue.put(render_id)
        return True

    def health_snapshot(self) -> dict[str, object]:
        return {
            "accepting_jobs": self.accepting_jobs,
            "worker_alive": bool(self._worker and not self._worker.done()),
            "queue_depth": self._queue.qsize(),
        }

    async def _run(self) -> None:
        while True:
            render_id = await self._queue.get()
            try:
                if self._executor is None:
                    from app.services.script_render_service import execute_script_render

                    await execute_script_render(render_id)
                else:
                    await self._executor(render_id)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - a failed render is persisted by the service
                logger.exception("Script render %s failed outside its persisted status", render_id)
            finally:
                self.enqueued_ids.discard(render_id)
                self._queue.task_done()


script_render_queue = ScriptRenderQueueManager()

