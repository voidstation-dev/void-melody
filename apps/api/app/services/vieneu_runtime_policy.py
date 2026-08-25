"""Hardware signature, runtime profiles, and candidate generation for adaptive VieNeu execution."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VieNeuRuntimeProfile:
    """Persisted hardware-specific runtime execution profile."""

    hardware_key: str
    device: str  # "cpu" | "cuda"
    backend: str  # "onnx" | "pytorch"
    precision: str  # "int8" | "fp16" | "fp32"
    inference_concurrency: int  # 1 to 4 for CPU
    threads_per_inference: int  # ONNX intra-op threads
    gpu_batch_size: int  # 1 to 16 for CUDA
    performance_mode: str = "auto"  # "auto" | "eco" | "performance"
    score: float | None = None
    tested_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VieNeuRuntimeProfile:
        return cls(
            hardware_key=data.get("hardware_key", "default"),
            device=data.get("device", "cpu"),
            backend=data.get("backend", "onnx"),
            precision=data.get("precision", "int8"),
            inference_concurrency=max(1, min(int(data.get("inference_concurrency", 1)), 4)),
            threads_per_inference=max(1, int(data.get("threads_per_inference", 4))),
            gpu_batch_size=max(1, min(int(data.get("gpu_batch_size", 1)), 16)),
            performance_mode=data.get("performance_mode", "auto"),
            score=data.get("score"),
            tested_at=data.get("tested_at"),
        )


def compute_hardware_key(
    device: str = "cpu",
    backend: str = "onnx",
    precision: str = "int8",
) -> str:
    """Generate a deterministic SHA256 hardware and engine signature."""
    cpu_count = os.cpu_count() or 1
    system_plat = platform.platform()
    machine = platform.machine()
    processor = platform.processor()

    gpu_name = "none"
    gpu_vram = 0
    if device == "cuda":
        try:
            import torch

            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_vram = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
        except Exception:
            gpu_name = "cuda_unavailable"

    raw_signature = "|".join([
        system_plat,
        machine,
        processor,
        str(cpu_count),
        device,
        backend,
        precision,
        gpu_name,
        str(gpu_vram),
    ])
    return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:32]


def get_default_profile(
    device: str = "cpu",
    backend: str = "onnx",
    precision: str = "int8",
    mode: str = "auto",
) -> VieNeuRuntimeProfile:
    """Safe bootstrap profile before autotuning."""
    cpu_count = os.cpu_count() or 1
    hw_key = compute_hardware_key(device, backend, precision)

    if device == "cuda":
        batch_size = 4 if mode == "performance" else (2 if mode == "auto" else 1)
        return VieNeuRuntimeProfile(
            hardware_key=hw_key,
            device="cuda",
            backend=backend,
            precision=precision,
            inference_concurrency=1,
            threads_per_inference=0,
            gpu_batch_size=batch_size,
            performance_mode=mode,
        )

    # CPU safe bounds: concurrency 1-4
    default_threads = min(max(cpu_count // 2, 1), 8)
    if mode == "eco":
        concurrency = 1
        threads = max(1, default_threads // 2)
    elif mode == "performance":
        concurrency = 2 if cpu_count >= 8 else 1
        threads = default_threads
    else:  # auto
        concurrency = 1
        threads = default_threads

    return VieNeuRuntimeProfile(
        hardware_key=hw_key,
        device="cpu",
        backend=backend,
        precision=precision,
        inference_concurrency=concurrency,
        threads_per_inference=threads,
        gpu_batch_size=1,
        performance_mode=mode,
    )


def generate_cpu_candidates(cpu_count: int) -> list[tuple[int, int]]:
    """Generate safe candidate pairs of (inference_concurrency, threads_per_inference).

    Strict limit: concurrency must never exceed 4.
    Leaves 15-25% headroom for UI, OS, FastAPI, and FFmpeg.
    """
    candidates: list[tuple[int, int]] = []
    # Always include the 1x baseline
    candidates.append((1, min(max(cpu_count - 1, 1), 8)))

    if cpu_count >= 4:
        candidates.append((2, max(1, (cpu_count - 2) // 2)))
    if cpu_count >= 8:
        candidates.append((2, max(2, (cpu_count - 2) // 2)))
        candidates.append((3, max(1, (cpu_count - 2) // 3)))
    if cpu_count >= 12:
        candidates.append((3, max(2, (cpu_count - 3) // 3)))
        candidates.append((4, max(1, (cpu_count - 4) // 4)))
    if cpu_count >= 16:
        candidates.append((4, max(2, (cpu_count - 4) // 4)))

    # Deduplicate while preserving order
    seen: set[tuple[int, int]] = set()
    result = []
    for c in candidates:
        if c not in seen and 1 <= c[0] <= 4:
            seen.add(c)
            result.append(c)
    return result


def get_profile_file_path() -> Path:
    data_dir = settings.audio_storage_dir.parent
    return data_dir / "vieneu_runtime_profile.json"


def load_persisted_profile() -> VieNeuRuntimeProfile | None:
    path = get_profile_file_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return VieNeuRuntimeProfile.from_dict(data)
    except Exception:
        logger.warning("Failed loading persisted VieNeu runtime profile", exc_info=True)
        return None


def persist_profile(profile: VieNeuRuntimeProfile) -> None:
    path = get_profile_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
        logger.info("Persisted VieNeu runtime profile: %s", profile)
    except Exception:
        logger.warning("Failed persisting VieNeu runtime profile", exc_info=True)
