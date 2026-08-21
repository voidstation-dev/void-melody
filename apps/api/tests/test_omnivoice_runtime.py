"""Tests for the OmniVoice isolated runtime client, worker protocol, error codes, and lifecycle."""

import asyncio
import os
import tempfile
from pathlib import Path
import pytest

from app.services.omnivoice_runtime import (
    OmniSynthesisRequest,
    OmniVoiceRuntimeClient,
    OmniVoiceRuntimeError,
)


@pytest.mark.asyncio
async def test_real_worker_does_not_fallback_to_mock():
    """Default worker must start in real mode and not silently fallback to mock."""
    client = OmniVoiceRuntimeClient(mock_mode=False)
    try:
        info = await client.get_runtime_info()
        assert info["mode"] == "real"
        assert info["model_loaded"] is False
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_real_worker_missing_package_fails():
    """Real worker must raise OMNI_PACKAGE_NOT_INSTALLED when omnivoice is missing."""
    client = OmniVoiceRuntimeClient(mock_mode=False)
    try:
        with pytest.raises(OmniVoiceRuntimeError) as exc_info:
            await client.load_model("dummy/path")
        assert exc_info.value.code == "OMNI_PACKAGE_NOT_INSTALLED"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_mock_worker_requires_explicit_mode():
    """Mock worker is only enabled when mock_mode=True is explicitly passed."""
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        info = await client.get_runtime_info()
        assert info["mode"] == "mock"
        assert info["package_installed"] is True
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_start_and_ping():
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        assert not client.is_running
        is_pong = await client.ping()
        assert is_pong is True
        assert client.is_running
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_load_and_unload_model():
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        load_res = await client.load_model("k2-fsa/OmniVoice", device="cpu")
        assert load_res["status"] == "loaded"

        info = await client.get_runtime_info()
        assert info["model_loaded"] is True

        unload_res = await client.unload_model()
        assert unload_res["status"] == "unloaded"

        info2 = await client.get_runtime_info()
        assert info2["model_loaded"] is False
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_synthesize(tmp_path: Path):
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        out_wav = tmp_path / "test_out.wav"
        request = OmniSynthesisRequest(
            text="Hello world test",
            output_path=str(out_wav),
            duration=1.5,
        )
        result = await client.synthesize(request)
        assert Path(result.output_path).is_file()
        assert result.sample_rate == 24000
        assert abs(result.duration_seconds - 1.5) < 0.1
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_create_and_validate_voice_prompt(tmp_path: Path):
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        audio_ref = tmp_path / "ref.wav"
        audio_ref.write_bytes(b"RIFF dummy wav data")
        out_prompt = tmp_path / "prompt.pt"

        res = await client.create_voice_prompt(
            audio_path=str(audio_ref),
            transcript="Test transcript",
            output_path=str(out_prompt),
        )
        assert Path(res["prompt_path"]).is_file()
        assert res["format"] == "omnivoice-voice-clone-prompt"

        val_res = await client.validate_voice_prompt(str(out_prompt))
        assert val_res["valid"] is True
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_timeout_terminates_worker_and_restarts_new_pid(tmp_path: Path):
    """PR18-R02: Timeout must terminate poisoned worker and subsequent call must get a fresh PID."""
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        old_pid = client.pid
        assert old_pid is not None

        out_wav = tmp_path / "timeout.wav"
        request = OmniSynthesisRequest(
            text="Long synthesis test",
            output_path=str(out_wav),
            simulate_delay_seconds=1.0,
        )

        # Call with very short timeout (50ms)
        with pytest.raises(OmniVoiceRuntimeError) as exc_info:
            await client.synthesize(request, timeout_seconds=0.05)
        assert exc_info.value.code == "OMNI_RUNTIME_TIMEOUT"

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
async def test_unknown_method_has_stable_code():
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        with pytest.raises(OmniVoiceRuntimeError) as exc_info:
            await client._call_rpc("non_existent_method")
        assert exc_info.value.code == "OMNI_METHOD_NOT_FOUND"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_invalid_params_has_stable_code():
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        await client.ensure_started()
        with pytest.raises(OmniVoiceRuntimeError) as exc_info:
            await client._call_rpc("synthesize", {"text": ""})
        assert exc_info.value.code == "OMNI_INVALID_PARAMS"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_mock_duration_is_bounded(tmp_path: Path):
    """PR18-R11: Mock synthesis duration is safely bounded."""
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        out_wav = tmp_path / "large_duration.wav"
        request = OmniSynthesisRequest(
            text="Test",
            output_path=str(out_wav),
            duration=99999.0,
        )
        result = await client.synthesize(request)
        assert result.duration_seconds <= 60.0
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_worker_path_outside_allowed_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """PR18-R10: Path validation rejects paths outside allowed roots."""
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    # Pass allowed roots to worker process
    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(allowed_dir))

    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        out_wav = outside_dir / "bad.wav"
        request = OmniSynthesisRequest(
            text="Test text",
            output_path=str(out_wav),
        )
        with pytest.raises(OmniVoiceRuntimeError) as exc_info:
            await client.synthesize(request)
        assert exc_info.value.code == "OMNI_PATH_OUTSIDE_ROOT"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_shutdown_is_idempotent_and_cleans_tasks():
    """PR18-R09: Shutdown can be called multiple times safely and tasks are completed."""
    client = OmniVoiceRuntimeClient(mock_mode=True)
    await client.ensure_started()
    assert client.is_running

    await client.shutdown()
    assert not client.is_running
    assert client._stdout_task is None
    assert client._stderr_task is None

    # Second shutdown should be safe no-op
    await client.shutdown()
    assert not client.is_running
