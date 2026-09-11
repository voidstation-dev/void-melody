"""Phase 4 tests: dedicated worker env bootstrap + provider runtime status.

The VoxCPM2 runtime must live in its own Python environment under
``data/envs/voxcpm`` (voxcpm needs Python <3.13; the FastAPI env is 3.14).
These tests pin the fail-fast codes, marker idempotency, and the
runtime_status truth table — all with monkeypatched data dirs, so no
real venv is created during the test run.
"""

from pathlib import Path

import pytest

import app.services.voxcpm_env as voxcpm_env
from app.providers.registry import VOXCPM2
from app.providers.runtime_status import get_provider_runtime_status
from app.services.voxcpm_env import (
    VOXCPM_INSTALL_MARKER,
    VOXCPM_WORKER_ENV_ID,
    VoxCpmEnvError,
    create_worker_env,
    env_exists,
    install_runtime,
    runtime_installed,
    worker_env_dir,
    worker_python_args,
    worker_python_executable,
)


@pytest.fixture
def env_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the worker env at a temp dir; returns the data dir."""
    monkeypatch.setattr(voxcpm_env, "_data_dir", tmp_path)
    monkeypatch.delenv("VOID_VOXCPM_PYTHON", raising=False)
    return tmp_path


def test_worker_env_dir_is_under_data_envs(env_root: Path):
    assert worker_env_dir() == env_root / "envs" / VOXCPM_WORKER_ENV_ID
    assert str(env_root / "envs" / "voxcpm") in str(worker_python_executable())


def test_worker_python_executable_platform_layout(env_root: Path):
    python = worker_python_executable()
    if voxcpm_env.os.name == "nt":
        assert python.name == "python.exe"
        assert python.parent.name == "Scripts"
    else:
        assert python.parent.name == "bin"


def test_env_exists_false_without_env(env_root: Path):
    assert env_exists() is False
    assert runtime_installed() is False


def test_runtime_installed_requires_marker(env_root: Path):
    env_dir = worker_env_dir()
    env_dir.mkdir(parents=True)
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")  # fake interpreter file

    assert env_exists() is True
    assert runtime_installed() is False  # env exists, marker missing

    (env_dir / VOXCPM_INSTALL_MARKER).write_text("ok", encoding="utf-8")
    assert runtime_installed() is True


def test_worker_python_args_include_script(env_root: Path):
    env_dir = worker_env_dir()
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")

    args = worker_python_args(mock_mode=False)
    assert str(python) in args
    assert any(arg.endswith("voxcpm-worker" + voxcpm_env.os.sep + "worker.py") or arg.endswith("voxcpm-worker/worker.py") for arg in args)
    assert "--mock" not in args

    assert "--mock" in worker_python_args(mock_mode=True)


def test_worker_python_args_fail_fast_without_env(env_root: Path):
    with pytest.raises(VoxCpmEnvError) as exc_info:
        worker_python_args(mock_mode=False)
    assert exc_info.value.code == "VOXCPM_RUNTIME_NOT_INSTALLED"


class _EmptyProbe:
    """Stand-in for subprocess.run: nothing found on py launcher / PATH."""

    returncode = 1
    stdout = ""
    stderr = ""


def test_create_worker_env_no_uv_no_python_fails_fast(env_root: Path, monkeypatch: pytest.MonkeyPatch):
    # Simulate: no uv on PATH, no VOID_VOXCPM_PYTHON, no existing env, and
    # no discoverable system interpreter (py launcher / python3.x on PATH).
    monkeypatch.setattr(voxcpm_env, "_uv_executable", lambda: None)
    monkeypatch.setattr(voxcpm_env.subprocess, "run", lambda *a, **k: _EmptyProbe())

    with pytest.raises(VoxCpmEnvError) as exc_info:
        create_worker_env()
    assert exc_info.value.code == "VOXCPM_ENV_NO_COMPATIBLE_PYTHON"


def test_create_worker_env_existing_env_is_idempotent(env_root: Path):
    env_dir = worker_env_dir()
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")

    result = create_worker_env()
    assert result == env_dir


def test_create_worker_env_fails_when_venv_command_fails(env_root: Path, monkeypatch: pytest.MonkeyPatch):
    """uv present but its venv command fails → VOXCPM_ENV_CREATE_FAILED."""
    monkeypatch.setattr(voxcpm_env, "_uv_executable", lambda: "uv")
    monkeypatch.setattr(voxcpm_env, "_find_compatible_python", lambda: None)

    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "uv venv exploded"

    def fake_run(command, **kwargs):
        assert command[0] == "uv"
        assert command[1] == "venv"
        return FakeResult()

    monkeypatch.setattr(voxcpm_env.subprocess, "run", fake_run)

    with pytest.raises(VoxCpmEnvError) as exc_info:
        create_worker_env()
    assert exc_info.value.code == "VOXCPM_ENV_CREATE_FAILED"
    assert "uv venv exploded" in exc_info.value.message


def test_create_worker_env_via_fallback_venv(env_root: Path, monkeypatch: pytest.MonkeyPatch):
    """No uv but a compatible interpreter override → python -m venv."""
    monkeypatch.setattr(voxcpm_env, "_uv_executable", lambda: None)
    monkeypatch.setattr(voxcpm_env, "_find_compatible_python", lambda: "C:/py312/python.exe")

    captured: dict = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        # Simulate the venv module actually creating the interpreter.
        python = worker_python_executable()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_bytes(b"")

        class Ok:
            returncode = 0
            stdout = ""
            stderr = ""

        return Ok()

    monkeypatch.setattr(voxcpm_env.subprocess, "run", fake_run)

    result = create_worker_env()
    assert result == worker_env_dir()
    assert captured["command"] == ["C:/py312/python.exe", "-m", "venv", str(worker_env_dir())]


def test_install_runtime_fails_fast_when_pip_fails(env_root: Path, monkeypatch: pytest.MonkeyPatch):
    env_dir = worker_env_dir()
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")

    class FakeResult:
        returncode = 1
        stdout = "line"
        stderr = "pip exploded: no wheels for this platform"

    monkeypatch.setattr(voxcpm_env.subprocess, "run", lambda command, **kwargs: FakeResult())

    with pytest.raises(VoxCpmEnvError) as exc_info:
        install_runtime(env_dir)
    assert exc_info.value.code == "VOXCPM_RUNTIME_INSTALL_FAILED"
    assert "no wheels" in exc_info.value.message
    assert runtime_installed() is False  # no marker written on failure


def test_install_runtime_idempotent_via_marker(env_root: Path, monkeypatch: pytest.MonkeyPatch):
    env_dir = worker_env_dir()
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")
    (env_dir / VOXCPM_INSTALL_MARKER).write_text("ok", encoding="utf-8")

    def boom(command, **kwargs):  # pip must never run when marker is present
        raise AssertionError("pip must not run when runtime is already installed")

    monkeypatch.setattr(voxcpm_env.subprocess, "run", boom)
    assert install_runtime(env_dir) == env_dir


def test_runtime_status_not_installed_before_env(env_root: Path):
    status = get_provider_runtime_status(VOXCPM2)
    assert status.status == "not_installed"
    assert status.installed is False
    assert status.available is False
    assert status.reason_code == "VOXCPM_RUNTIME_NOT_INSTALLED"


def test_runtime_status_not_installed_with_env_but_no_marker(env_root: Path):
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")

    status = get_provider_runtime_status(VOXCPM2)
    assert status.status == "not_installed"
    assert status.installed is True  # env exists...
    assert status.available is False  # ...but runtime package is missing
    assert status.reason_code == "VOXCPM_RUNTIME_NOT_INSTALLED"


def test_runtime_status_ready_with_marker(env_root: Path):
    python = worker_python_executable()
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")
    (worker_env_dir() / VOXCPM_INSTALL_MARKER).write_text("ok", encoding="utf-8")

    status = get_provider_runtime_status(VOXCPM2)
    assert status.status == "ready"
    assert status.installed is True
    assert status.available is True
    assert status.model_installed is True
    assert status.reason_code is None
    # Model load state is worker truth, not install truth:
    assert status.model_loaded is False