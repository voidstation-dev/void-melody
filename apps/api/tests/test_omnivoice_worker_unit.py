"""Unit tests for OmniVoice worker backend contracts, path security, and lifecycle."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any
import numpy as np
import pytest

# Add worker directory to sys.path for direct component unit testing
WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "omnivoice-worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from backend import OmniBackend  # noqa: E402
from errors import (  # noqa: E402
    OMNI_ALLOWED_ROOTS_NOT_CONFIGURED,
    OMNI_INFERENCE_FAILED,
    OMNI_INVALID_PARAMS,
    OMNI_PATH_OUTSIDE_ROOT,
    WorkerError,
)
from path_utils import validate_path  # noqa: E402
from real_backend import RealOmniBackend  # noqa: E402
from worker import OmniVoiceWorker  # noqa: E402
from app.services.omnivoice_runtime import (  # noqa: E402
    OmniSynthesisRequest,
    OmniVoiceRuntimeClient,
    OmniVoiceRuntimeError,
)


class FakeOmniVoiceModel:
    def __init__(self, device: str = "cpu", sampling_rate: int = 24000) -> None:
        self.device = device
        self.sampling_rate = sampling_rate
        self.last_generate_kwargs: dict[str, Any] = {}
        self.return_audios: list[np.ndarray] = [np.zeros(48000, dtype=np.float32)]

    @classmethod
    def from_pretrained(cls, model_path: str, **kwargs: Any) -> "FakeOmniVoiceModel":
        device_map = kwargs.get("device_map", "cpu")
        return cls(device=device_map)

    def generate(self, **kwargs: Any) -> list[np.ndarray]:
        self.last_generate_kwargs = kwargs
        return self.return_audios


def test_real_backend_load_model_uses_device_map(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F13: load_model must call OmniVoice.from_pretrained with device_map."""
    backend = RealOmniBackend()
    backend._import_error = None

    model_dir = tmp_path / "fake_model"
    model_dir.mkdir()

    # Pass allowed roots to bypass path security
    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(tmp_path))

    class FakeOmniVoiceModule:
        OmniVoice = FakeOmniVoiceModel

    monkeypatch.setitem(sys.modules, "omnivoice", FakeOmniVoiceModule)

    res = backend.load_model({"model_path": str(model_dir), "device": "cuda:0"})
    assert res["status"] == "loaded"
    assert res["device"] == "cuda:0"
    assert backend.model is not None
    assert backend.device == "cuda:0"


def test_real_backend_synthesis_unwraps_audio_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F13: synthesis must unwrap audios[0] and use model.sampling_rate."""
    backend = RealOmniBackend()
    backend._import_error = None

    fake_model = FakeOmniVoiceModel(device="cpu", sampling_rate=24000)
    fake_model.return_audios = [np.zeros(24000 * 3, dtype=np.float32)]  # 3 seconds
    backend.model = fake_model

    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(tmp_path))

    out_file = tmp_path / "out.wav"
    res = backend.synthesize({"text": "Hello world", "output_path": str(out_file)})

    assert res["output_path"] == str(out_file)
    assert res["sample_rate"] == 24000
    assert abs(res["duration_seconds"] - 3.0) < 1e-3
    assert out_file.exists()


def test_real_backend_uses_model_sampling_rate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F13: synthesis must adapt when model exposes custom sample rate."""
    backend = RealOmniBackend()
    backend._import_error = None

    fake_model = FakeOmniVoiceModel(device="cpu", sampling_rate=48000)
    fake_model.return_audios = [np.zeros(48000 * 2, dtype=np.float32)]  # 2 seconds
    backend.model = fake_model

    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(tmp_path))

    out_file = tmp_path / "out48k.wav"
    res = backend.synthesize({"text": "Hello 48k", "output_path": str(out_file)})

    assert res["sample_rate"] == 48000
    assert abs(res["duration_seconds"] - 2.0) < 1e-3


def test_real_backend_empty_audio_list_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F13: Empty return list from generate() must raise OMNI_INFERENCE_FAILED."""
    backend = RealOmniBackend()
    backend._import_error = None

    fake_model = FakeOmniVoiceModel(device="cpu")
    fake_model.return_audios = []  # empty
    backend.model = fake_model

    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(tmp_path))

    out_file = tmp_path / "empty.wav"
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize({"text": "Fail test", "output_path": str(out_file)})
    assert exc_info.value.code == OMNI_INFERENCE_FAILED


def test_real_mode_without_allowed_roots_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F16: Without VOID_OMNI_ALLOWED_ROOTS, path validation in real mode must fail closed."""
    monkeypatch.delenv("VOID_OMNI_ALLOWED_ROOTS", raising=False)
    monkeypatch.delenv("OMNIVOICE_WORKER_MODE", raising=False)

    with pytest.raises(WorkerError) as exc_info:
        validate_path(str(tmp_path / "test.wav"))
    assert exc_info.value.code == OMNI_ALLOWED_ROOTS_NOT_CONFIGURED


def test_allowed_root_accepts_child_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F16: Paths inside allowed roots are accepted."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    child = allowed / "sub" / "audio.wav"

    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(allowed))
    res = validate_path(str(child))
    assert res == child.resolve()


def test_allowed_root_rejects_sibling_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """PR18-F16: Paths outside allowed roots are rejected."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    sibling = tmp_path / "other" / "audio.wav"

    monkeypatch.setenv("VOID_OMNI_ALLOWED_ROOTS", str(allowed))
    with pytest.raises(WorkerError) as exc_info:
        validate_path(str(sibling))
    assert exc_info.value.code == OMNI_PATH_OUTSIDE_ROOT


def test_non_object_params_has_stable_error():
    """PR18-F16/Section 7: Non-dict params in worker request must raise OMNI_INVALID_PARAMS."""
    class FakeBackend:
        def ping(self, _params: Any) -> dict[str, Any]:
            return {"pong": True}

    worker = OmniVoiceWorker(FakeBackend())  # type: ignore

    import io
    import json

    # Mock dispatch with non-dict params
    request = {"id": "req-1", "method": "ping", "params": "not-a-dict"}
    raw_req = json.dumps(request) + "\n"

    old_stdin = sys.stdin
    old_stdout = sys.stdout
    try:
        sys.stdin = io.StringIO(raw_req)
        sys.stdout = io.StringIO()
        worker.run()
        out = sys.stdout.getvalue().strip()
        resp = json.loads(out)
        assert resp["ok"] is False
        assert resp["error"]["code"] == OMNI_INVALID_PARAMS
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout


@pytest.mark.asyncio
async def test_repeated_timeout_restart_does_not_leak_tasks(tmp_path: Path):
    """PR18-F15: Repeated timeout and recovery cleanly reaps processes and does not leak tasks."""
    client = OmniVoiceRuntimeClient(mock_mode=True)
    try:
        out_wav = tmp_path / "timeout_leak_test.wav"
        request = OmniSynthesisRequest(
            text="Simulated slow generation",
            output_path=str(out_wav),
            simulate_delay_seconds=0.5,
        )

        for _ in range(3):
            with pytest.raises(OmniVoiceRuntimeError) as exc_info:
                await client.synthesize(request, timeout_seconds=0.05)
            assert exc_info.value.code == "OMNI_RUNTIME_TIMEOUT"
            assert not client.is_running
            assert client._stdout_task is None
            assert client._stderr_task is None

        # Verify client can still successfully start fresh and serve requests
        pong = await client.ping()
        assert pong is True
        assert client.is_running
    finally:
        await client.shutdown()
