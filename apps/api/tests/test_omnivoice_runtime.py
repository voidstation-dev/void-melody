"""Tests for the OmniVoice isolated runtime client and worker protocol."""

import asyncio
import tempfile
from pathlib import Path
import pytest

from app.services.omnivoice_runtime import (
    OmniSynthesisRequest,
    OmniVoiceRuntimeClient,
    OmniVoiceRuntimeError,
)


@pytest.mark.asyncio
async def test_client_start_and_ping():
    client = OmniVoiceRuntimeClient()
    try:
        assert not client.is_running
        is_pong = await client.ping()
        assert is_pong is True
        assert client.is_running
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_runtime_info():
    client = OmniVoiceRuntimeClient()
    try:
        info = await client.get_runtime_info()
        assert info["omnivoice_version"] == "0.2.1"
        assert "device" in info
        assert "pid" in info
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_load_and_unload_model():
    client = OmniVoiceRuntimeClient()
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
    client = OmniVoiceRuntimeClient()
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
async def test_client_create_voice_prompt(tmp_path: Path):
    client = OmniVoiceRuntimeClient()
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
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_timeout():
    client = OmniVoiceRuntimeClient()
    try:
        await client.ensure_started()
        with pytest.raises(OmniVoiceRuntimeError) as exc_info:
            await client._call_rpc("synthesize", {"text": "Long text", "output_path": "dummy"}, timeout_seconds=0.0001)
        assert exc_info.value.code == "OMNI_RUNTIME_TIMEOUT"
    finally:
        await client.shutdown()


@pytest.mark.asyncio
async def test_client_restart_after_crash():
    client = OmniVoiceRuntimeClient()
    try:
        await client.ensure_started()
        assert client.is_running

        # Force kill worker process
        if client._process:
            client._process.kill()
            await client._process.wait()

        # Next call should transparently auto-recover
        pong = await client.ping()
        assert pong is True
        assert client.is_running
    finally:
        await client.shutdown()
