"""In-memory cancellation registry for 0-latency worker cancellation checks."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class CancellationRegistry:
    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def register(self, job_id: str) -> asyncio.Event:
        async with self._lock:
            if job_id not in self._events:
                self._events[job_id] = asyncio.Event()
            return self._events[job_id]

    def get_event(self, job_id: str) -> asyncio.Event | None:
        return self._events.get(job_id)

    async def cancel(self, job_id: str) -> bool:
        async with self._lock:
            event = self._events.get(job_id)
            if event is not None:
                event.set()
                logger.info("Signaled in-memory cancellation for job %s", job_id)
                return True
            # Even if not yet registered in memory, register it as already cancelled
            event = asyncio.Event()
            event.set()
            self._events[job_id] = event
            return True

    def is_cancelled(self, job_id: str) -> bool:
        event = self._events.get(job_id)
        return event.is_set() if event is not None else False

    async def unregister(self, job_id: str) -> None:
        async with self._lock:
            self._events.pop(job_id, None)


cancellation_registry = CancellationRegistry()
