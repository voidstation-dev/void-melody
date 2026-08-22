"""Tests for the runtime probe and model manager.

These tests do NOT load the real VieNeu model (it is ~GB and needs network).
They test the probe logic and the manager's concurrency/unload behavior using a
stub engine factory.
"""

import asyncio
import sys

import pytest

from vieneu_core.engine import ModelManager, RuntimeProbe, probe_runtime


def test_probe_runtime_returns_runtime_probe():
    probe = probe_runtime()
    assert isinstance(probe, RuntimeProbe)
    assert probe.device in {"cpu", "cuda"}
    assert probe.backend in {"onnx", "pytorch"}
    assert probe.cpu_count >= 1
    assert probe.threads == 0
    assert isinstance(probe.platform, str)


def test_probe_runtime_on_cpu_without_torch():
    """On the CI/dev machine the probe should at least report a CPU path."""
    probe = probe_runtime()
    if not probe.torch_cuda_available:
        assert probe.device == "cpu"
        assert probe.backend == "onnx"


@pytest.mark.asyncio
async def test_model_manager_loads_once_and_shares_instance():
    calls = []

    def factory():
        calls.append(1)
        return object()

    manager = ModelManager(engine_factory=factory)
    assert manager.is_loaded() is False

    # Concurrent get_engine calls must result in a single load.
    engines = await asyncio.gather(manager.get_engine(), manager.get_engine())
    assert len(calls) == 1
    assert engines[0] is engines[1]
    assert manager.is_loaded() is True


@pytest.mark.asyncio
async def test_model_manager_unload_releases_instance():
    loaded = []

    class FakeEngine:
        def __init__(self):
            loaded.append(1)

        def close(self):
            loaded.append("closed")

    manager = ModelManager(engine_factory=FakeEngine)
    await manager.get_engine()
    assert manager.is_loaded() is True
    manager.unload()
    assert manager.is_loaded() is False
    assert "closed" in loaded


@pytest.mark.asyncio
async def test_model_manager_serializes_loads():
    """Two concurrent loads must not create two engines."""
    order = []

    async def slow_factory():
        order.append("start")
        await asyncio.sleep(0.01)
        order.append("end")
        return object()

    # ModelManager runs the factory in an executor; emulate slowness there.

    def sync_slow_factory():
        import time

        order.append("start")
        time.sleep(0.01)
        order.append("end")
        return object()

    manager = ModelManager(engine_factory=sync_slow_factory)
    await asyncio.gather(manager.get_engine(), manager.get_engine())
    # Only one load happened.
    assert order.count("start") == 1
    assert order.count("end") == 1


@pytest.mark.asyncio
async def test_default_factory_uses_bootstrapped_local_model_paths(monkeypatch, tmp_path):
    calls = []

    class FakeVieneu:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    fake_vieneu = type("M", (), {"Vieneu": FakeVieneu})
    monkeypatch.setitem(sys.modules, "vieneu", fake_vieneu)
    (tmp_path / "backbone").mkdir()
    (tmp_path / "onnx_int8").mkdir()
    (tmp_path / "codec").mkdir()
    monkeypatch.setenv("VIENEU_V3_TURBO_MODEL_DIR", str(tmp_path / "backbone"))
    monkeypatch.setenv("VIENEU_V3_TURBO_ONNX_DIR", str(tmp_path / "onnx_int8"))
    monkeypatch.setenv("VIENEU_V3_TURBO_CODEC_DIR", str(tmp_path / "codec"))

    manager = ModelManager()
    await manager.get_engine()

    assert calls == [
        {
            "mode": "v3turbo",
            "backbone_repo": str(tmp_path / "backbone"),
            "onnx_dir": str(tmp_path / "onnx_int8"),
            "codec_dir": str(tmp_path / "codec"),
            "device": "auto",
            "backend": "auto",
            "precision": "int8",
        }
    ]
