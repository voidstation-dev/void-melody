"""Runtime probe and singleton model manager for the VieNeu engine.

This module wraps `from vieneu import Vieneu` behind a framework-agnostic
surface so apps/api (Phase 5) and VOID STUDIO (future) can share one model
instance. Resource policy: model load concurrency = 1, model instance is
singleton/shared — never one-per-queue-worker.

The actual TTS call (``Vieneu(mode="v3turbo").infer(...)``) is wired in Phase 5;
this phase provides the probe + lazy singleton manager.
"""

from __future__ import annotations

import asyncio
import os
import platform
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeProbe:
    """Snapshot of the local runtime capabilities relevant to VieNeu."""

    device: str  # "cpu" | "cuda"
    backend: str  # "onnx" | "pytorch"
    onnxruntime_available: bool
    torch_available: bool
    torch_cuda_available: bool
    cpu_count: int
    threads: int  # 0 = engine default
    platform: str
    # Clone enrollment imports the speaker frontend lazily, so ONNX Runtime
    # alone is not evidence that cloning works. These fields are deliberately
    # booleans: capability responses must not expose local filesystem paths.
    torchaudio_available: bool = False
    speaker_encoder_artifact_available: bool = False
    denoiser_artifact_available: bool = False
    codec_encoder_artifact_available: bool = False


def _importable(module_name: str) -> bool:
    try:
        import importlib

        importlib.import_module(module_name)
        return True
    except Exception:  # noqa: BLE001 - capability probing must never crash the API
        return False


def _artifact_roots(*environment_names: str) -> list[Path]:
    roots: list[Path] = []
    for name in environment_names:
        value = os.environ.get(name)
        if value:
            roots.append(Path(value))

    # The packaged app can point VIENEU_HF_HOME at a pre-populated cache. Keep
    # this lookup narrow and deterministic instead of scanning the whole disk.
    hf_home = os.environ.get("VIENEU_HF_HOME") or os.environ.get("HF_HOME")
    if hf_home:
        hub = Path(hf_home) / "hub"
    else:
        try:
            from huggingface_hub.constants import HF_HUB_CACHE
            hub = Path(HF_HUB_CACHE)
        except ImportError:
            hub = Path.home() / ".cache" / "huggingface" / "hub"
            
    roots.extend(
        path
        for pattern in (
            "models--pnnbao-ump--VieNeu-TTS-v3-Turbo/snapshots/*",
            "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX/snapshots/*",
        )
        for path in hub.glob(pattern)
        if path.is_dir()
    )
    return roots


def _artifact_available(filename: str, *environment_names: str) -> bool:
    for root in _artifact_roots(*environment_names):
        candidate = root / filename
        if candidate.is_file() and candidate.stat().st_size > 0:
            return True
    return False


def probe_runtime() -> RuntimeProbe:
    """Probe the local runtime without loading the model.

    On Apple Silicon, ``device`` resolves to ``"cpu"`` (the v3 Turbo path does
    not use MPS) and the torch-free ONNX engine runs on CPU.
    """

    cpu_count = os.cpu_count() or 1
    onnx_available = _importable("onnxruntime")
    torch_available = _importable("torch")
    torchaudio_available = _importable("torchaudio")
    torch_cuda = False
    if torch_available:
        try:
            import torch  # type: ignore

            torch_cuda = bool(torch.cuda.is_available())
        except Exception:  # noqa: BLE001 - a broken optional torch install is unavailable
            torch_cuda = False
    device = "cuda" if torch_cuda else "cpu"
    # v3 Turbo: auto → ONNX on CPU, PyTorch on CUDA.
    backend = "pytorch" if torch_cuda else "onnx"
    threads = 0  # 0 = engine default (min(max(cpu_count // 2, 1), 8))
    return RuntimeProbe(
        device=device,
        backend=backend,
        onnxruntime_available=onnx_available,
        torch_available=torch_available,
        torch_cuda_available=torch_cuda,
        cpu_count=cpu_count,
        threads=threads,
        platform=platform.platform(),
        torchaudio_available=torchaudio_available,
        speaker_encoder_artifact_available=_artifact_available(
            "speaker_encoder.onnx",
            "VIENEU_CLONE_ARTIFACT_DIR",
            "VIENEU_V3_TURBO_MODEL_DIR",
        ),
        denoiser_artifact_available=_artifact_available(
            "denoiser.onnx",
            "VIENEU_CLONE_ARTIFACT_DIR",
            "VIENEU_V3_TURBO_MODEL_DIR",
        ),
        codec_encoder_artifact_available=_artifact_available(
            "moss_audio_tokenizer_encode.onnx",
            "VIENEU_CODEC_ARTIFACT_DIR",
            "VIENEU_V3_TURBO_CODEC_DIR",
        ),
    )


class ModelManager:
    """Singleton manager for the shared VieNeu engine instance.

    Resource policy: exactly one model instance per process. Load concurrency
    is 1 (an ``asyncio.Lock`` serializes loads). Callers obtain the shared
    instance via :meth:`get_engine`; the first call loads lazily.
    """

    def __init__(
        self,
        *,
        engine_factory: Callable[[], Any] | None = None,
        load_timeout_seconds: float | None = None,
    ) -> None:
        self._engine_factory = engine_factory
        self._engine: Any | None = None
        self._load_lock = asyncio.Lock()
        self._load_timeout = load_timeout_seconds

    def is_loaded(self) -> bool:
        return self._engine is not None

    async def get_engine(self) -> Any:
        """Return the shared engine instance, loading it on first call."""
        if self._engine is not None:
            return self._engine
        async with self._load_lock:
            # Re-check inside the lock (another task may have loaded it).
            if self._engine is not None:
                return self._engine
            factory = self._engine_factory or self._default_factory
            loop = asyncio.get_running_loop()
            if self._load_timeout is not None:
                self._engine = await asyncio.wait_for(
                    loop.run_in_executor(None, factory),
                    timeout=self._load_timeout,
                )
            else:
                self._engine = await loop.run_in_executor(None, factory)
        return self._engine

    def unload(self) -> None:
        """Release the engine instance (best-effort close)."""
        if self._engine is not None:
            close = getattr(self._engine, "close", None)
            if callable(close):
                try:
                    close()
                except RuntimeError:
                    pass
        self._engine = None

    @staticmethod
    def _default_factory() -> Any:
        """Default factory constructing the real VieNeu v3 Turbo engine.

        Sets ``HF_HOME`` if ``VIENEU_HF_HOME`` is present so the manager can
        point Vieneu at a pre-populated cache (Phase 4 downloader).
        """
        hf_home = os.environ.get("VIENEU_HF_HOME")
        if hf_home:
            os.environ.setdefault("HF_HOME", hf_home)
        from vieneu import Vieneu  # type: ignore

        return Vieneu(mode="v3turbo", device="auto", backend="auto", precision="int8")
