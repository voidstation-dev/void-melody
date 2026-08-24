"""TTS Queue Manager backed by the Unified Provider-Aware Scheduler."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings
from app.providers.capcut_provider import CapCutProvider
from app.providers.vieneu_provider import VieneuProvider
from app.scheduler.cancellation import cancellation_registry
from app.scheduler.lanes import ExecutionLane
from app.scheduler.policies import ProviderExecutionPolicy
from app.services.job_recovery import requeue_interrupted_job
from app.services.provider_circuit_breaker import ProviderCircuitBreaker
from app.workers.tts_worker import execute_tts_job_step

logger = logging.getLogger(__name__)


class TTSQueueManager:
    """Provider-aware queue manager maintaining isolated execution lanes."""

    def __init__(
        self,
        concurrency: int | None = None,
        *,
        provider_registry: dict[str, Any] | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
        shutdown_grace_seconds: float | None = None,
    ):
        self.circuit_breaker = circuit_breaker or ProviderCircuitBreaker(
            failure_threshold=settings.tts_circuit_breaker_failure_threshold,
            window_seconds=settings.tts_circuit_breaker_window_seconds,
            cooldown_seconds=settings.tts_circuit_breaker_cooldown_seconds,
        )
        self.provider_registry = provider_registry or {
            "capcut": CapCutProvider(
                catalog_path=settings.capcut_catalog_path,
                timeout_seconds=settings.tts_provider_timeout_seconds,
                circuit_breaker=self.circuit_breaker,
            ),
            "vieneu": VieneuProvider(),
        }
        self.shutdown_grace_seconds = (
            settings.tts_queue_shutdown_grace_seconds
            if shutdown_grace_seconds is None
            else shutdown_grace_seconds
        )

        self.lanes: dict[str, ExecutionLane] = {}
        if concurrency is not None:
            self.lanes["capcut"] = ExecutionLane(
                name="capcut",
                policy=ProviderExecutionPolicy(
                    "capcut",
                    concurrency,
                    settings.capcut_chunk_concurrency,
                ),
                worker_executor=self._execute_tts_job,
                shutdown_grace_seconds=self.shutdown_grace_seconds,
            )
        else:
            self.lanes["capcut"] = ExecutionLane(
                name="capcut",
                policy=ProviderExecutionPolicy(
                    "capcut",
                    settings.capcut_job_concurrency,
                    settings.capcut_chunk_concurrency,
                ),
                worker_executor=self._execute_tts_job,
                shutdown_grace_seconds=self.shutdown_grace_seconds,
            )
            self.lanes["vieneu"] = ExecutionLane(
                name="vieneu",
                policy=ProviderExecutionPolicy(
                    "vieneu",
                    settings.vieneu_job_concurrency,
                    settings.vieneu_chunk_concurrency,
                ),
                worker_executor=self._execute_tts_job,
                shutdown_grace_seconds=self.shutdown_grace_seconds,
            )

        self._accepting_jobs = False

    @property
    def accepting_jobs(self) -> bool:
        return self._accepting_jobs

    @accepting_jobs.setter
    def accepting_jobs(self, val: bool) -> None:
        self._accepting_jobs = val
        for lane in self.lanes.values():
            lane.accepting_jobs = val

    @property
    def concurrency(self) -> int:
        return sum(lane.policy.job_concurrency for lane in self.lanes.values())

    @property
    def queue(self) -> Any:
        return self.lanes["capcut"].queue

    @property
    def workers(self) -> list[asyncio.Task]:
        all_workers: list[asyncio.Task] = []
        for lane in self.lanes.values():
            all_workers.extend(lane.workers)
        return all_workers

    @property
    def delayed_tasks(self) -> set[asyncio.Task]:
        all_tasks: set[asyncio.Task] = set()
        for lane in self.lanes.values():
            all_tasks.update(lane.delayed_tasks)
        return all_tasks

    @property
    def enqueued_ids(self) -> set[str]:
        all_ids: set[str] = set()
        for lane in self.lanes.values():
            all_ids.update(lane.enqueued_ids)
        return all_ids

    async def start(self) -> None:
        self.accepting_jobs = True
        logger.info("Starting TTSQueueManager execution lanes")
        for lane in self.lanes.values():
            await lane.start()

    async def stop(self) -> None:
        self.accepting_jobs = False
        logger.info("Stopping TTSQueueManager execution lanes")
        for lane in self.lanes.values():
            await lane.stop()

    async def enqueue(
        self,
        job_id: str,
        batch_position: int = 0,
        provider_id: str | None = None,
    ) -> bool:
        if not self.accepting_jobs:
            raise RuntimeError("Queue manager is not accepting jobs")

        lane_name = "capcut"
        if provider_id and provider_id in self.lanes:
            lane_name = provider_id

        # Register in-memory cancellation
        await cancellation_registry.register(job_id)

        return await self.lanes[lane_name].enqueue(job_id, batch_position=batch_position)

    async def enqueue_after(
        self,
        job_id: str,
        *,
        delay_seconds: float,
        batch_position: int = 0,
        provider_id: str | None = None,
    ) -> None:
        lane_name = "capcut"
        if provider_id and provider_id in self.lanes:
            lane_name = provider_id

        await self.lanes[lane_name].enqueue_after(
            job_id,
            delay_seconds=delay_seconds,
            batch_position=batch_position,
        )

    def health_snapshot(self) -> dict[str, object]:
        total_workers = sum(lane.policy.job_concurrency for lane in self.lanes.values())
        alive_workers = sum(
            sum(1 for w in lane.workers if not w.done()) for lane in self.lanes.values()
        )
        total_depth = sum(lane.queue.qsize() for lane in self.lanes.values())

        return {
            "accepting_jobs": self.accepting_jobs,
            "worker_count": total_workers,
            "workers_alive": alive_workers,
            "queue_depth": total_depth,
            "circuit_breaker": self.circuit_breaker.snapshot(),
            "lanes": {name: lane.health_snapshot() for name, lane in self.lanes.items()},
        }

    async def _execute_tts_job(self, job_id: str, worker_id: int) -> None:
        try:
            await execute_tts_job_step(
                job_id,
                provider_registry=self.provider_registry,
                worker_id=worker_id,
            )
        except asyncio.CancelledError:
            await asyncio.shield(requeue_interrupted_job(job_id))
            raise
        finally:
            await cancellation_registry.unregister(job_id)


queue_manager = TTSQueueManager()
