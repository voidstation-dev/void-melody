"""Unified Provider-Aware Scheduler coordinating dedicated execution lanes."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.tts_job import TTSJobModel
from app.providers.capcut_provider import CapCutProvider
from app.providers.vieneu_provider import VieneuProvider
from app.scheduler.cancellation import cancellation_registry
from app.scheduler.lanes import ExecutionLane
from app.scheduler.policies import (
    ProviderExecutionPolicy,
    get_default_policies,
    select_execution_lane,
)
from app.services.provider_circuit_breaker import ProviderCircuitBreaker
from app.workers.tts_worker import execute_tts_job_step

logger = logging.getLogger(__name__)


class UnifiedScheduler:
    def __init__(
        self,
        *,
        policies: dict[str, ProviderExecutionPolicy] | None = None,
        provider_registry: dict[str, Any] | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
        shutdown_grace_seconds: float | None = None,
    ) -> None:
        self.policies = policies or get_default_policies()
        self.shutdown_grace_seconds = (
            settings.tts_queue_shutdown_grace_seconds
            if shutdown_grace_seconds is None
            else shutdown_grace_seconds
        )
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

        # Create isolated execution lanes
        self.lanes: dict[str, ExecutionLane] = {
            "capcut": ExecutionLane(
                name="capcut",
                policy=self.policies.get(
                    "capcut",
                    ProviderExecutionPolicy("capcut", settings.capcut_job_concurrency, settings.capcut_chunk_concurrency),
                ),
                worker_executor=self._execute_tts_job,
                shutdown_grace_seconds=self.shutdown_grace_seconds,
            ),
            "vieneu": ExecutionLane(
                name="vieneu",
                policy=self.policies.get(
                    "vieneu",
                    ProviderExecutionPolicy("vieneu", settings.vieneu_job_concurrency, settings.vieneu_chunk_concurrency),
                ),
                worker_executor=self._execute_tts_job,
                shutdown_grace_seconds=self.shutdown_grace_seconds,
            ),
        }

        self.accepting_jobs = False

    @property
    def concurrency(self) -> int:
        return sum(lane.policy.job_concurrency for lane in self.lanes.values())

    @concurrency.setter
    def concurrency(self, value: int) -> None:
        # Compatibility setter for legacy tests modifying concurrency
        if "capcut" in self.lanes:
            self.lanes["capcut"].policy = ProviderExecutionPolicy(
                "capcut", value, self.lanes["capcut"].policy.chunk_concurrency
            )

    @property
    def queue(self) -> Any:
        # Compatibility property returning default lane queue for tests that inspect queue
        return self.lanes["capcut"].queue

    @property
    def workers(self) -> list[asyncio.Task]:
        # Compatibility property returning all active workers across lanes
        all_workers = []
        for lane in self.lanes.values():
            all_workers.extend(lane.workers)
        return all_workers

    @property
    def enqueued_ids(self) -> set[str]:
        # Compatibility property returning all enqueued ids across lanes
        all_ids: set[str] = set()
        for lane in self.lanes.values():
            all_ids.update(lane.enqueued_ids)
        return all_ids

    async def start(self) -> None:
        self.accepting_jobs = True
        logger.info("Starting UnifiedScheduler lanes")
        for lane in self.lanes.values():
            await lane.start()

    async def stop(self) -> None:
        self.accepting_jobs = False
        logger.info("Stopping UnifiedScheduler lanes")
        for lane in self.lanes.values():
            await lane.stop()

    async def enqueue(
        self,
        job_id: str,
        batch_position: int = 0,
        provider_id: str | None = None,
    ) -> bool:
        if not self.accepting_jobs:
            raise RuntimeError("UnifiedScheduler is not accepting jobs")

        resolved_provider = provider_id
        if not resolved_provider:
            # Lookup provider_id from database if not passed
            async with AsyncSessionLocal() as session:
                job = await session.get(TTSJobModel, job_id)
                if job:
                    resolved_provider = job.provider_id

        lane = select_execution_lane(self.lanes, resolved_provider)

        # Register in-memory cancellation event
        await cancellation_registry.register(job_id)

        return await lane.enqueue(job_id, batch_position=batch_position)

    async def enqueue_after(
        self,
        job_id: str,
        *,
        delay_seconds: float,
        batch_position: int = 0,
        provider_id: str | None = None,
    ) -> None:
        lane = select_execution_lane(self.lanes, provider_id)
        await lane.enqueue_after(
            job_id,
            delay_seconds=delay_seconds,
            batch_position=batch_position,
        )

    async def cancel(self, job_id: str) -> bool:
        return await cancellation_registry.cancel(job_id)

    def health_snapshot(self) -> dict[str, object]:
        total_workers = sum(lane.policy.job_concurrency for lane in self.lanes.values())
        alive_workers = sum(
            sum(1 for w in lane.workers if not w.done()) for lane in self.lanes.values()
        )
        total_depth = sum(lane.queue.qsize() for lane in self.lanes.values())

        lane_snapshots = {
            name: lane.health_snapshot() for name, lane in self.lanes.items()
        }

        return {
            "accepting_jobs": self.accepting_jobs,
            "worker_count": total_workers,
            "workers_alive": alive_workers,
            "queue_depth": total_depth,
            "circuit_breaker": self.circuit_breaker.snapshot(),
            "lanes": lane_snapshots,
        }

    async def _execute_tts_job(self, job_id: str, worker_id: int) -> None:
        try:
            await execute_tts_job_step(
                job_id,
                provider_registry=self.provider_registry,
                worker_id=worker_id,
            )
        finally:
            await cancellation_registry.unregister(job_id)


unified_scheduler = UnifiedScheduler()
