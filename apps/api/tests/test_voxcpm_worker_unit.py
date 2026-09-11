"""Unit tests for VoxCPM2 worker backend contracts, path security, and dispatcher."""

import sys
from pathlib import Path

import pytest

WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "voxcpm-worker"
WORKER_MODULE_NAMES = ("backend", "errors", "path_utils", "mock_backend", "real_backend", "worker")

for _name in WORKER_MODULE_NAMES:
    sys.modules.pop(_name, None)
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from backend import VoxCpmBackend  # noqa: E402
from errors import (  # noqa: E402
    VOXCPM_ALLOWED_ROOTS_NOT_CONFIGURED,
    VOXCPM_INVALID_PARAMS,
    VOXCPM_METHOD_NOT_FOUND,
    VOXCPM_MODEL_NOT_LOADED,
    VOXCPM_PATH_OUTSIDE_ROOT,
    WorkerError,
)
from path_utils import validate_path, validate_path_or_mock  # noqa: E402
from mock_backend import MockVoxCpmBackend  # noqa: E402
from real_backend import RealVoxCpmBackend  # noqa: E402
from worker import VoxCpmWorker  # noqa: E402


def test_backend_contract_has_required_methods():
    for method in (
        "ping",
        "runtime_info",
        "load_model",
        "unload_model",
        "warmup",
        "analyze_reference",
        "synthesize_clone",
        "synthesize_emotional",
        "synthesize_ultimate",
    ):
        assert hasattr(VoxCpmBackend, method), f"Missing backend method: {method}"


def test_mock_ping_and_runtime_info():
    backend = MockVoxCpmBackend()
    assert backend.ping() == {"pong": True, "mock": True, "mode": "mock"}
    info = backend.runtime_info()
    assert info["backend"] == "mock"
    assert info["sample_rate"] == 48000


def test_mock_warmup_requires_model():
    backend = MockVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.warmup()
    assert exc_info.value.code == VOXCPM_MODEL_NOT_LOADED


def test_mock_synthesis_requires_model(tmp_path: Path):
    backend = MockVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_clone({"text": "hi", "output_path": str(tmp_path / "a.wav")})
    assert exc_info.value.code == VOXCPM_MODEL_NOT_LOADED


def test_mock_synthesis_writes_48k_wav(tmp_path: Path):
    backend = MockVoxCpmBackend()
    backend.load_model({"device": "cpu"})
    out = tmp_path / "out.wav"
    result = backend.synthesize_clone({"text": "hi", "output_path": str(out), "duration": 2.0})
    assert Path(result["output_path"]).is_file()
    assert result["sample_rate"] == 48000


def test_mock_synthesis_requires_text(tmp_path: Path):
    backend = MockVoxCpmBackend()
    backend.load_model({})
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_emotional({"output_path": str(tmp_path / "b.wav")})
    assert exc_info.value.code == VOXCPM_INVALID_PARAMS


def test_mock_synthesis_duration_bounded(tmp_path: Path):
    backend = MockVoxCpmBackend()
    backend.load_model({})
    result = backend.synthesize_clone(
        {"text": "hi", "output_path": str(tmp_path / "c.wav"), "duration": 99999.0}
    )
    assert result["duration_seconds"] <= 60.0


def test_mock_analyze_reference_shape(tmp_path: Path):
    backend = MockVoxCpmBackend()
    result = backend.analyze_reference({"audio_path": str(tmp_path / "ref.wav"), "duration": 6.0})
    assert result["sample_rate"] == 48000
    assert result["duration_seconds"] == 6.0
    assert "quality_score" in result


def test_path_validation_rejects_outside_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    monkeypatch.setenv("VOID_VOXCPM_ALLOWED_ROOTS", str(allowed))

    ok = validate_path_or_mock(str(allowed / "x.wav"))
    assert ok.name == "x.wav"

    with pytest.raises(WorkerError) as exc_info:
        validate_path_or_mock(str(tmp_path / "outside" / "y.wav"))
    assert exc_info.value.code == VOXCPM_PATH_OUTSIDE_ROOT


def test_path_validation_requires_roots(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VOID_VOXCPM_ALLOWED_ROOTS", raising=False)
    with pytest.raises(WorkerError) as exc_info:
        validate_path("relative/path.wav")
    assert exc_info.value.code == VOXCPM_ALLOWED_ROOTS_NOT_CONFIGURED


def test_real_backend_ping_reports_real_mode():
    backend = RealVoxCpmBackend()
    assert backend.ping()["mode"] == "real"
    info = backend.runtime_info()
    assert info["backend"] == "real"
    assert info["package_installed"] is False


def test_real_backend_never_falls_back_to_mock(tmp_path: Path):
    backend = RealVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_clone({"text": "hi", "output_path": str(tmp_path / "d.wav")})
    # Either guard is fail-fast and stable; the invariant is no mock fallback.
    assert exc_info.value.code in ("VOXCPM_PACKAGE_NOT_INSTALLED", "VOXCPM_MODEL_NOT_LOADED")


def _dispatch(worker: VoxCpmWorker, method: str, params: dict):
    responses = []

    original = worker._respond
    worker._respond = lambda req_id, result=None, error=None: (  # type: ignore[method-assign]
        responses.append({"id": req_id, "result": result, "error": error}),
        original(req_id, result=result, error=error),
    )[0]
    worker._dispatch("req-1", method, params)
    worker._respond = original  # type: ignore[method-assign]
    return responses


def test_dispatcher_unknown_method_code():
    worker = VoxCpmWorker(MockVoxCpmBackend())
    responses = _dispatch(worker, "bogus_method", {})
    assert responses[0]["error"]["code"] == VOXCPM_METHOD_NOT_FOUND


def test_dispatcher_handles_worker_error():
    worker = VoxCpmWorker(MockVoxCpmBackend())
    responses = _dispatch(worker, "synthesize_clone", {"text": "hi"})
    assert responses[0]["error"]["code"] == VOXCPM_MODEL_NOT_LOADED


def test_dispatcher_rejects_non_dict_params():
    worker = VoxCpmWorker(MockVoxCpmBackend())
    responses = []
    worker._respond = lambda req_id, result=None, error=None: responses.append(  # type: ignore[method-assign]
        {"id": req_id, "error": error}
    )
    worker._dispatch("req-1", "ping", ["not", "a", "dict"])
    assert responses[0]["error"]["code"] == VOXCPM_INVALID_PARAMS