"""Tests for the VoxCPM2 isolated runtime client, worker protocol, and lifecycle.

Exit criteria (Phase 2): worker starts, ping passes, runtime_info passes,
mock load/unload passes, timeout terminates poisoned worker + crash recovery,
clean shutdown, no fallback to VieNeu/CapCut.
"""

import asyncio
from pathlib import Path

import pytest

from app.services.voxcpm_runtime import (
    VoxCpmRuntimeClient,
    VoxCpmRuntimeError,
    VoxCpmSynthesisRequest,
)


@pytest.mark.asyncio
async def test_worker_starts_and_ping_passes():
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        assert not client.is_running
        assert await client.ping() is True
        assert client.is_running
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_runtime_info_reports_mock_backend():
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        info = await client.get_runtime_info()
        assert info["backend"] == "mock"
        assert info["model_loaded"] is False
        assert info["sample_rate"] == 48000
        assert info["ready"] is True
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_mock_load_and_unload_model():
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        load_res = await client.load_model("openbmb/VoxCPM2", device="cpu")
        assert load_res["status"] == "loaded"
        assert load_res["backend"] == "mock"

        info = await client.get_runtime_info()
        assert info["model_loaded"] is True

        unload_res = await client.unload_model()
        assert unload_res["status"] == "unloaded"

        info2 = await client.get_runtime_info()
        assert info2["model_loaded"] is False
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_mock_synthesize_clone_writes_48k_wav(tmp_path: Path):
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        await client.load_model(device="cpu")
        out_wav = tmp_path / "clone_out.wav"
        request = VoxCpmSynthesisRequest(
            text="Xin chào VoxCPM2",
            output_path=str(out_wav),
            reference_wav_path=str(tmp_path / "ref.wav"),
            duration=1.5,
        )
        result = await client.synthesize(request, method="synthesize_clone")
        assert Path(result.output_path).is_file()
        assert result.sample_rate == 48000
        assert abs(result.duration_seconds - 1.5) < 0.1
        assert result.method == "synthesize_clone"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_mock_synthesize_emotional_requires_model(tmp_path: Path):
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        out_wav = tmp_path / "emo.wav"
        request = VoxCpmSynthesisRequest(text="test", output_path=str(out_wav))
        with pytest.raises(VoxCpmRuntimeError) as exc_info:
            await client.synthesize(request, method="synthesize_emotional")
        assert exc_info.value.code == "VOXCPM_MODEL_NOT_LOADED"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_mock_synthesize_emotional_with_instruction(tmp_path: Path):
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        await client.load_model(device="cpu")
        out_wav = tmp_path / "emo.wav"
        request = VoxCpmSynthesisRequest(
            text="Anh vẫn nhớ ngày hôm đó.",
            output_path=str(out_wav),
            instruction="sad, restrained, speaking slowly",
        )
        result = await client.synthesize(request, method="synthesize_emotional")
        assert Path(result.output_path).is_file()
        assert result.sample_rate == 48000
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_synthesis_method_whitelist():
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        request = VoxCpmSynthesisRequest(text="t", output_path=str(Path("x.wav")))
        with pytest.raises(VoxCpmRuntimeError) as exc_info:
            await client.synthesize(request, method="synthesize_not_real")
        assert exc_info.value.code == "VOXCPM_METHOD_NOT_FOUND"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_timeout_terminates_worker_and_restarts_new_pid(tmp_path: Path):
    """Timeout must terminate poisoned worker; next call must get a fresh PID."""
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        old_pid = client.pid
        assert old_pid is not None

        out_wav = tmp_path / "timeout.wav"
        request = VoxCpmSynthesisRequest(
            text="Long synthesis test",
            output_path=str(out_wav),
            simulate_delay_seconds=1.0,
        )

        with pytest.raises(VoxCpmRuntimeError) as exc_info:
            await client.synthesize(request, timeout_seconds=0.05)
        assert exc_info.value.code == "VOXCPM_RUNTIME_TIMEOUT"

        # Worker must have been killed
        assert not client.is_running

        # Next call must transparently start a fresh worker with a different PID
        pong = await client.ping()
        assert pong is True
        assert client.is_running
        new_pid = client.pid
        assert new_pid is not None
        assert new_pid != old_pid
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_crash_recovery_fails_pending_and_recovers(tmp_path: Path):
    """If the worker dies mid-request, pending requests fail with VOXCPM_RUNTIME_CRASHED
    and a subsequent call transparently starts a fresh worker."""
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        proc = client._process
        assert proc is not None

        out_wav = tmp_path / "crash.wav"
        request = VoxCpmSynthesisRequest(
            text="Crash test",
            output_path=str(out_wav),
            simulate_delay_seconds=5.0,
        )

        task = asyncio.create_task(client.synthesize(request))
        await asyncio.sleep(0.3)
        proc.kill()
        with pytest.raises(VoxCpmRuntimeError) as exc_info:
            await task
        assert exc_info.value.code == "VOXCPM_RUNTIME_CRASHED"

        # Recovery: fresh worker handles a new request
        pong = await client.ping()
        assert pong is True
        assert client.is_running
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_unknown_method_has_stable_code():
    client = VoxCpmRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        with pytest.raises(VoxCpmRuntimeError) as exc_info:
            await client._call_rpc("non_existent_method")
        assert exc_info.value.code == "VOXCPM_METHOD_NOT_FOUND"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_shutdown_is_idempotent():
    client = VoxCpmRuntimeClient(mock_mode=True)
    await client.ensure_started()
    assert client.is_running

    await client.shutdown()
    assert not client.is_running
    assert client._stdout_task is None
    assert client._stderr_task is None

    # Second shutdown is a safe no-op
    await client.shutdown()
    assert not client.is_running


@pytest.mark.asyncio
async def test_real_client_requires_dedicated_env(tmp_path, monkeypatch):
    """Real mode must refuse to spawn the worker from the FastAPI interpreter.

    Points the env bootstrap at an empty temp dir so the dedicated env does
    not exist (even if one is installed in the real data dir), so
    constructing the client fails fast with VOXCPM_RUNTIME_NOT_INSTALLED.
    """
    import app.services.voxcpm_env as voxcpm_env

    monkeypatch.setattr(voxcpm_env, "_data_dir", tmp_path)
    with pytest.raises(Exception) as exc_info:
        VoxCpmRuntimeClient(mock_mode=False)
    assert "VOXCPM_RUNTIME_NOT_INSTALLED" in str(getattr(exc_info.value, "code", exc_info.value))


@pytest.mark.asyncio
async def test_real_worker_reports_not_ready_without_package():
    """Real worker must not silently fall back to mock mode.

    Runs the real backend in a throwaway venv-free way: point the client at
    the current interpreter but a copied worker script; the real backend
    reports package_installed=False and load_model fails with a stable code.
    """
    import shutil
    import sys as _sys
    import tempfile
    from pathlib import Path as _Path

    worker_dir = _Path(__file__).resolve().parents[2] / "voxcpm-worker"
    tmp_dir = _Path(tempfile.mkdtemp(prefix="voxcpm-worker-test-"))
    shutil.copy(worker_dir / "worker.py", tmp_dir / "worker.py")
    for module in ("backend.py", "errors.py", "path_utils.py", "mock_backend.py", "real_backend.py"):
        shutil.copy(worker_dir / module, tmp_dir / module)

    client = VoxCpmRuntimeClient(
        worker_script_path=tmp_dir / "worker.py",
        python_executable=_sys.executable,
        mock_mode=False,
    )
    try:
        info = await client.get_runtime_info()
        assert info["backend"] == "real"
        assert info["package_installed"] is False
        # Real backend without voxcpm package must fail with a stable code.
        with pytest.raises(VoxCpmRuntimeError) as exc_info:
            await client.load_model("openbmb/VoxCPM2")
        assert exc_info.value.code == "VOXCPM_PACKAGE_NOT_INSTALLED"
    finally:
        await client.shutdown()
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_worker_script_missing_raises_not_installed(tmp_path: Path):
    client = VoxCpmRuntimeClient(
        worker_script_path=tmp_path / "missing_worker.py", mock_mode=True
    )
    with pytest.raises(VoxCpmRuntimeError) as exc_info:
        await client.ensure_started()
    assert exc_info.value.code == "VOXCPM_RUNTIME_NOT_INSTALLED"