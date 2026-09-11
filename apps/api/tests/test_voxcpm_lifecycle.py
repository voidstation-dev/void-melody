"""Phase 10 tests: Settings & model lifecycle.

Separation of concerns: /voxcpm/installation answers *installation*
questions (worker env, runtime package, model cache); /voxcpm/runtime-state
answers *process* questions. The dedicated env is never the FastAPI main
environment.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_async_session
from app.main import app
from app.services import voxcpm_lifecycle as lifecycle
from app.services.voxcpm_env import (
    VOXCPM_INSTALL_MARKER,
    worker_env_dir,
    worker_python_executable,
)
from tests.conftest import pro_entitlement_auth


@pytest.fixture(autouse=True)
def _pro_auth(pro_entitlement_auth):  # noqa: F811
    yield


@pytest.fixture
def patch_env(tmp_path: Path, monkeypatch):
    """Point the worker env at a temp dir with a fake python executable."""
    env_dir = tmp_path / "envs" / "voxcpm"
    scripts = env_dir / "Scripts" if __import__("os").name == "nt" else env_dir / "bin"
    scripts.mkdir(parents=True, exist_ok=True)
    python = scripts / ("python.exe" if __import__("os").name == "nt" else "python")
    python.write_text("", encoding="utf-8")

    from app.services import voxcpm_env

    monkeypatch.setattr(voxcpm_env, "worker_env_dir", lambda: env_dir)
    monkeypatch.setattr(voxcpm_env, "worker_python_executable", lambda: python)
    # lifecycle imports the names directly — patch there too
    monkeypatch.setattr(lifecycle, "worker_env_dir", lambda: env_dir)
    monkeypatch.setattr(lifecycle, "worker_python_executable", lambda: python)
    return env_dir


@pytest.fixture
def patch_model_cache(tmp_path: Path, monkeypatch):
    """Point the HF cache at a temp dir; optionally materialize a snapshot."""
    hub = tmp_path / "hub" / "models--openbmb--VoxCPM2"

    def make_snapshot(with_config: bool = True):
        snap = hub / "snapshots" / "abc123"
        snap.mkdir(parents=True, exist_ok=True)
        if with_config:
            (snap / "config.json").write_text("{}", encoding="utf-8")
        (hub / "blobs").mkdir(parents=True, exist_ok=True)
        (hub / "blobs" / "b1").write_bytes(b"x" * 1024)
        return snap

    monkeypatch.setattr(lifecycle, "_model_cache_dir", lambda: hub)
    return make_snapshot


# ---------------------------------------------------------------------------
# Installation status
# ---------------------------------------------------------------------------


def test_installation_status_not_installed(patch_env, patch_model_cache):
    status = lifecycle.get_installation_status()
    assert status["provider_id"] == "voxcpm2"
    assert status["env_present"] is True
    assert status["package_installed"] is False  # no install marker
    assert status["model_status"] == "not_downloaded"


def test_installation_status_with_marker_and_model(patch_env, patch_model_cache):
    (patch_env / VOXCPM_INSTALL_MARKER).write_text("ok", encoding="utf-8")
    patch_model_cache()
    status = lifecycle.get_installation_status()
    assert status["package_installed"] is True
    assert status["model_status"] == "downloaded"
    assert status["downloaded_bytes"] > 0
    assert status["sample_rate"] == 48000


def test_installation_status_env_missing(tmp_path, monkeypatch, patch_model_cache):
    monkeypatch.setattr(lifecycle, "worker_env_dir", lambda: tmp_path / "missing")
    monkeypatch.setattr(lifecycle, "worker_python_executable", lambda: tmp_path / "missing" / "python.exe")
    status = lifecycle.get_installation_status()
    assert status["env_present"] is False
    assert status["package_installed"] is False
    assert status["model_status"] == "not_downloaded"


def test_snapshot_without_config_counts_as_not_downloaded(patch_env, patch_model_cache):
    patch_model_cache(with_config=False)
    status = lifecycle.get_installation_status()
    assert status["model_status"] == "not_downloaded"


# ---------------------------------------------------------------------------
# Verify / install / remove
# ---------------------------------------------------------------------------


def test_verify_raises_when_env_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle, "worker_python_executable", lambda: tmp_path / "nope.exe")
    with pytest.raises(lifecycle.VoxCpmLifecycleError) as exc_info:
        lifecycle.verify_installation()
    assert exc_info.value.code == "VOXCPM_RUNTIME_NOT_INSTALLED"


def test_verify_runs_import_inside_dedicated_env(patch_env, monkeypatch):
    import subprocess as _subprocess

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        result = _subprocess.CompletedProcess(cmd, 0, stdout="0.2.5", stderr="")
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", fake_run)
    result = lifecycle.verify_installation()
    assert result["ok"] is True
    assert result["version"] == "0.2.5"
    # The verification command must use the dedicated env python, never
    # the FastAPI main interpreter (plan rule 10).
    assert str(patch_env) in captured["cmd"][0]


def test_remove_env_deletes_directory(patch_env):
    assert patch_env.is_dir()
    result = lifecycle.remove_installation()
    assert result["env_removed"] is True
    assert not patch_env.is_dir()


def test_remove_env_when_missing_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle, "worker_env_dir", lambda: tmp_path / "missing")
    result = lifecycle.remove_installation()
    assert result["env_removed"] is False


def test_remove_model_cache_deletes_dir(patch_env, patch_model_cache):
    patch_model_cache()
    cache_dir = lifecycle._model_cache_dir()
    assert cache_dir.is_dir()
    result = lifecycle.remove_model_cache()
    assert result["model_removed"] is True
    assert not cache_dir.is_dir()


# ---------------------------------------------------------------------------
# Runtime state (process/model state — separate from installation)
# ---------------------------------------------------------------------------


def test_runtime_state_separate_from_installation(patch_env, patch_model_cache):
    (patch_env / VOXCPM_INSTALL_MARKER).write_text("ok", encoding="utf-8")
    patch_model_cache()
    state = lifecycle.get_runtime_state()
    assert state["package_installed"] is True
    assert state["model_downloaded"] is True
    # Runtime state says nothing about worker running / model loaded —
    # that belongs to the live worker probe (runtime_info RPC).
    assert "worker_running" not in state
    assert "model_loaded" not in state


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client(patch_env):
    async def override_get_async_session():
        raise AssertionError("lifecycle endpoints must not touch the database")

    app.dependency_overrides[get_async_session] = override_get_async_session
    try:
        transport = ASGITransport(app=app)
        yield AsyncClient(transport=transport, base_url="http://test")
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_installation_endpoint_returns_snapshot(client):
    response = await client.get("/api/v1/voxcpm/installation")
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "voxcpm2"
    assert "package_installed" in data
    assert "model_status" in data


@pytest.mark.asyncio
async def test_runtime_state_endpoint(client):
    response = await client.get("/api/v1/voxcpm/runtime-state")
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "voxcpm2"
    assert "model_downloaded" in data


@pytest.mark.asyncio
async def test_verify_endpoint_409_when_env_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle, "worker_python_executable", lambda: tmp_path / "nope.exe")

    async def override_get_async_session():
        raise AssertionError("no db")

    app.dependency_overrides[get_async_session] = override_get_async_session
    try:
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        response = await client.post("/api/v1/voxcpm/installation/verify")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "VOXCPM_RUNTIME_NOT_INSTALLED"
        await client.aclose()
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_download_progress_endpoint(patch_env, patch_model_cache, client):
    make = patch_model_cache()
    (lifecycle._model_cache_dir() / "blobs" / "big").write_bytes(b"x" * 2048)
    response = await client.get("/api/v1/voxcpm/installation/download-progress")
    assert response.status_code == 200
    data = response.json()
    assert data["complete"] is True
    assert data["downloaded_bytes"] >= 2048
    assert data["expected_bytes"] > 0