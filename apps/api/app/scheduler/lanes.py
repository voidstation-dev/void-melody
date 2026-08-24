"""Isolated execution lanes for TTS providers to prevent cross-provider starvation."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.scheduler.policies import ProviderExecutionPolicy

logger = logging.getLogger(__name__)


class ExecutionLane:
    def __init__(
        self,
        name: str,
        policy: ProviderExecutionPolicy,
        worker_executor: Callable[[str, int], Awaitable[None]],
        shutdown_grace_seconds: float = 15.0,
    ) -> None:
        self.name = name
        self.policy = policy
        self.worker_executor = worker_executor
        self.shutdown_grace_seconds = shutdown_grace_seconds

        self.queue: asyncio.PriorityQueue[tuple[int, float, str]] = asyncio.PriorityQueue()
        self.workers: list[asyncio.Task] = []
        self.delayed_tasks: set[asyncio.Task] = set()
        self.enqueued_ids: set[str] = set()
        self._lock = asyncio.Lock()
        self.accepting_jobs = False

    async def start(self) -> None:
        if self.workers:
            return
        self.accepting_jobs = True
        logger.info("Starting execution lane '%s' with %d workers", self.name, self.policy.job_concurrency)
        for worker_id in range(self.policy.job_concurrency):
            self.workers.append(
                asyncio.create_task(
                    self._worker_loop(worker_id),
                    name=f"lane-{self.name}-{worker_id}",
                )
            )

    async def stop(self) -> None:
        self.accepting_jobs = False
        logger.info("Stopping execution lane '%s'", self.name)

        for task in self.delayed_tasks:
            task.cancel()
        await asyncio.gather(*self.delayed_tasks, return_exceptions=True)
        self.delayed_tasks.clear()

        try:
            await asyncio.wait_for(
                self.queue.join(),
                timeout=self.shutdown_grace_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Lane '%s' shutdown grace period expired", self.name)

        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        while not self.queue.empty():
            try:
                _, _, job_id = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            async with self._lock:
                self.enqueued_ids.discard(job_id)
            self.queue.task_done()

    async def enqueue(self, job_id: str, batch_position: int = 0) -> bool:
        async with self._lock:
            if not self.accepting_jobs:
                raise RuntimeError(f"Lane '{self.name}' is not accepting jobs")
            if job_id in self.enqueued_ids:
                return False
            self.enqueued_ids.add(job_id)

        try:
            await self.queue.put((batch_position, time.time(), job_id))
        except BaseException:
            async with self._lock:
                self.enqueued_ids.discard(job_id)
            raise
        logger.info("Enqueued job %s to lane '%s'; queue depth=%s", job_id, self.name, self.queue.qsize())
        return True

    async def enqueue_after(
        self,
        job_id: str,
        *,
        delay_seconds: float,
        batch_position: int = 0,
    ) -> None:
        async def delayed_enqueue() -> None:
            await asyncio.sleep(delay_seconds)
            await self.enqueue(job_id, batch_position)

        task = asyncio.create_task(
            delayed_enqueue(),
            name=f"retry-{self.name}-{job_id}",
        )
        self.delayed_tasks.add(task)
        task.add_done_callback(self.delayed_tasks.discard)

    def health_snapshot(self) -> dict[str, object]:
        return {
            "name": self.name,
            "accepting_jobs": self.accepting_jobs,
            "worker_count": self.policy.job_concurrency,
            "chunk_concurrency": self.policy.chunk_concurrency,
            "workers_alive": sum(1 for worker in self.workers if not worker.done()),
            "queue_depth": self.queue.qsize(),
        }

    async def _worker_loop(self, worker_id: int) -> None:
        logger.info("Lane '%s' worker %d started", self.name, worker_id)
        while True:
            try:
                _, _, job_id = await self.queue.get()
            except asyncio.CancelledError:
                return

            try:
                await self.worker_executor(job_id, worker_id)
            except asyncio.CancelledError:
                # Requeue on cancellation during shutdown
                from app.services.job_recovery import requeue_interrupted_job
                await asyncio.shield(requeue_interrupted_job(job_id))
                raise
            except Exception:
                logger.exception("Lane '%s' worker %d failed processing job %s", self.name, worker_id, job_id)
            finally:
                async with self._lock:
                    self.enqueued_ids.discard(job_id)
                self.queue.task_done()
