"""Lightweight automated runtime benchmark and tuning for local VieNeu execution."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.services.vieneu_runtime_policy import (
    VieNeuRuntimeProfile,
    compute_hardware_key,
    generate_cpu_candidates,
    get_default_profile,
    persist_profile,
)

logger = logging.getLogger(__name__)

BENCHMARK_SAMPLE_TEXT = (
    "Xin chào, đây là câu văn mẫu tiếng Việt được sử dụng để kiểm tra tốc độ "
    "và tối ưu hóa hệ thống tổng hợp giọng nói Void Melody trên thiết bị phần cứng của bạn."
)


async def run_autotune(
    engine: Any,
    *,
    device: str = "cpu",
    backend: str = "onnx",
    precision: str = "int8",
    mode: str = "auto",
    sample_text: str = BENCHMARK_SAMPLE_TEXT,
) -> VieNeuRuntimeProfile:
    """Run a fast 5-10s micro-benchmark to discover the optimal local runtime configuration."""
    hw_key = compute_hardware_key(device, backend, precision)
    logger.info("Starting VieNeu autotune for hardware key: %s (mode: %s)", hw_key, mode)

    # 1. Warm engine once
    try:
        await asyncio.to_thread(
            engine.infer,
            text="Khởi động.",
            voice="BV421_vivn_streaming",
            apply_watermark=False,
        )
    except Exception:
        logger.warning("Engine warmup before autotune encountered error", exc_info=True)

    char_count = len(sample_text)

    # 2. CUDA Path: Benchmark Batch Sizes
    if device == "cuda" and backend == "pytorch":
        batch_candidates = [1, 2, 4, 8, 16]
        best_batch = 1
        best_time = float("inf")

        for bs in batch_candidates:
            if mode == "eco" and bs > 4:
                continue
            texts = [sample_text] * bs
            try:
                start = time.monotonic()
                await asyncio.to_thread(
                    engine.infer_batch,
                    texts=texts,
                    voice="BV421_vivn_streaming",
                    batch_size=bs,
                    apply_watermark=False,
                )
                elapsed = time.monotonic() - start
                per_text_time = elapsed / bs
                logger.info("CUDA batch candidate %d: %.3fs per item (total %.3fs)", bs, per_text_time, elapsed)
                if per_text_time < best_time:
                    best_time = per_text_time
                    best_batch = bs
            except Exception as exc:
                logger.warning("CUDA batch size %d failed (possibly OOM): %s", bs, exc)
                break  # Stop probing higher batch sizes

        throughput = char_count / max(best_time, 0.001)
        profile = VieNeuRuntimeProfile(
            hardware_key=hw_key,
            device="cuda",
            backend="pytorch",
            precision=precision,
            inference_concurrency=1,
            threads_per_inference=0,
            gpu_batch_size=best_batch,
            performance_mode=mode,
            score=round(throughput, 2),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
        persist_profile(profile)
        return profile

    # 3. CPU Path: Benchmark Concurrency x Threads
    cpu_count = os.cpu_count() or 1
    candidates = generate_cpu_candidates(cpu_count)

    best_cand = (1, min(max(cpu_count // 2, 1), 8))
    best_throughput = 0.0

    for conc, threads in candidates:
        if mode == "eco" and conc > 1:
            continue
        try:
            # Test sequential vs bounded concurrent execution
            start = time.monotonic()
            tasks = [
                asyncio.to_thread(
                    engine.infer,
                    text=sample_text,
                    voice="BV421_vivn_streaming",
                    apply_watermark=False,
                )
                for _ in range(conc)
            ]
            await asyncio.gather(*tasks)
            elapsed = time.monotonic() - start

            total_chars = char_count * conc
            throughput = total_chars / max(elapsed, 0.001)
            logger.info(
                "CPU candidate %dx%d: %.3fs (throughput: %.1f chars/s)",
                conc,
                threads,
                elapsed,
                throughput,
            )

            # In Auto mode, slightly favor lower concurrency if throughput gain is marginal (<10%)
            if throughput > best_throughput * (1.05 if mode == "auto" else 1.0):
                best_throughput = throughput
                best_cand = (conc, threads)

        except Exception as exc:
            logger.warning("CPU candidate %dx%d failed: %s", conc, threads, exc)

    profile = VieNeuRuntimeProfile(
        hardware_key=hw_key,
        device="cpu",
        backend=backend,
        precision=precision,
        inference_concurrency=best_cand[0],
        threads_per_inference=best_cand[1],
        gpu_batch_size=1,
        performance_mode=mode,
        score=round(best_throughput, 2),
        tested_at=datetime.now(timezone.utc).isoformat(),
    )
    persist_profile(profile)
    return profile
