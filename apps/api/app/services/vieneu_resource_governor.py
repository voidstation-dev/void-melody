"""Centralized resource governor coordinating VieNeu inference concurrency, threads, and GPU batching."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings
from app.services.vieneu_auto_tuner import run_autotune
from app.services.vieneu_runtime_policy import (
    VieNeuRuntimeProfile,
    compute_hardware_key,
    get_default_profile,
    load_persisted_profile,
    persist_profile,
)

logger = logging.getLogger(__name__)


class VieNeuResourceGovernor:
    """Coordinates local machine resource utilization for VieNeu execution."""

    def __init__(self) -> None:
        self._profile: VieNeuRuntimeProfile | None = None
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(1)
        self._lock: asyncio.Lock = asyncio.Lock()
        self._initialized: bool = False
        self._batch_size: int = 1

    async def initialize(
        self,
        device: str = "cpu",
        backend: str = "onnx",
        precision: str = "int8",
        mode: str = "auto",
    ) -> VieNeuRuntimeProfile:
        async with self._lock:
            if self._initialized and self._profile is not None:
                return self._profile

            expected_hw_key = compute_hardware_key(device, backend, precision)
            persisted = load_persisted_profile()

            if (
                persisted is not None
                and persisted.hardware_key == expected_hw_key
                and persisted.device == device
                and persisted.backend == backend
            ):
                logger.info("Loaded matching persisted VieNeu profile: %s", persisted)
                self._profile = persisted
            else:
                logger.info("Using default bootstrap VieNeu profile for key %s", expected_hw_key)
                self._profile = get_default_profile(device, backend, precision, mode)

            self._apply_profile(self._profile)
            self._initialized = True
            return self._profile

    def _apply_profile(self, profile: VieNeuRuntimeProfile) -> None:
        concurrency = max(1, min(profile.inference_concurrency, settings.vieneu_max_cpu_concurrency))
        self._semaphore = asyncio.Semaphore(concurrency)
        self._batch_size = max(1, profile.gpu_batch_size)
        logger.info(
            "Applied VieNeu runtime policy: concurrency=%d, threads=%d, batch_size=%d (mode: %s)",
            concurrency,
            profile.threads_per_inference,
            self._batch_size,
            profile.performance_mode,
        )

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore

    @property
    def gpu_batch_size(self) -> int:
        return self._batch_size

    @property
    def profile(self) -> VieNeuRuntimeProfile:
        if self._profile is None:
            self._profile = get_default_profile()
        return self._profile

    def handle_cuda_oom(self) -> int:
        """Dynamically halve CUDA batch size upon OOM without crashing."""
        if self._batch_size > 1:
            self._batch_size = max(1, self._batch_size // 2)
            logger.warning("CUDA OOM detected: reduced batch size to %d", self._batch_size)
        return self._batch_size

    async def reoptimize(
        self,
        engine: Any,
        device: str = "cpu",
        backend: str = "onnx",
        precision: str = "int8",
        mode: str = "auto",
    ) -> VieNeuRuntimeProfile:
        """Run on-demand re-benchmarking and apply the new profile."""
        async with self._lock:
            new_profile = await run_autotune(
                engine,
                device=device,
                backend=backend,
                precision=precision,
                mode=mode,
            )
            self._profile = new_profile
            self._apply_profile(new_profile)
            return new_profile


vieneu_governor = VieNeuResourceGovernor()
