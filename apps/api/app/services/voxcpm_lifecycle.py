"""VoxCPM2 model lifecycle service (Phase 10).

Separation of concerns from the plan:
- **Settings** manages *installation*: is the worker env + runtime installed,
  is the HF model present, download/verify/remove actions.
- **Runtime tab** manages the current *process/model state*: worker running,
  model loaded, device, backend.

This module only answers installation questions and drives env/model
lifecycle. It never touches the shared TTS pipeline and never falls back to
other providers.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.services.voxcpm_env import (
    VoxCpmEnvError,
    worker_env_dir,
    worker_python_executable,
)

logger = logging.getLogger(__name__)

VOXCPM_MODEL_ID = "openbmb/VoxCPM2"


class VoxCpmLifecycleError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _model_cache_dir() -> Path:
    """HF cache location for the VoxCPM2 checkpoint.

    The worker env resolves HF_HOME itself; the API process inspects the
    same default location (``~/.cache/huggingface``) unless overridden.
    """
    import os

    hf_home = os.environ.get(
        "HF_HOME",
        str(Path.home() / ".cache" / "huggingface"),
    )
    return Path(hf_home) / "hub" / "models--openbmb--VoxCPM2"


def _model_snapshot_dir() -> Path | None:
    cache_dir = _model_cache_dir()
    snapshots = cache_dir / "snapshots"
    if not snapshots.is_dir():
        return None
    # A snapshot is "present" when its config.json exists (the HF layout
    # materializes files as downloads complete).
    for snapshot in sorted(snapshots.iterdir()):
        if (snapshot / "config.json").is_file():
            return snapshot
    return None


def _model_total_bytes() -> int:
    cache_dir = _model_cache_dir()
    if not cache_dir.is_dir():
        return 0
    total = 0
    for blob in (cache_dir / "blobs").glob("*"):
        try:
            total += blob.stat().st_size
        except OSError:
            continue
    return total


def get_installation_status() -> dict[str, Any]:
    """Installation snapshot for the Settings tab."""
    env_ready = worker_python_executable().is_file()
    marker = (worker_env_dir() / "voxcpm-runtime.installed").is_file()
    package_installed = env_ready and marker
    snapshot = _model_snapshot_dir()
    model_status = "not_downloaded"
    if snapshot is not None:
        model_status = "downloaded"
    downloaded_bytes = _model_total_bytes()
    return {
        "provider_id": "voxcpm2",
        "model_id": VOXCPM_MODEL_ID,
        "env_present": env_ready,
        "package_installed": package_installed,
        "model_status": model_status,
        "model_snapshot": str(snapshot) if snapshot else None,
        "downloaded_bytes": downloaded_bytes,
        "storage_dir": str(_model_cache_dir()),
        "sample_rate": 48000,
        # Device compatibility: torch CPU is the guaranteed floor; CUDA/MPS
        # depend on the host. The worker resolves `device="auto"` at load.
        "device_policy": "auto",
    }


def verify_installation() -> dict[str, Any]:
    """Verify env + runtime package + importability of voxcpm.

    Runs ``python -c "import voxcpm"`` inside the dedicated env only —
    never the FastAPI main environment (plan rule 10).
    """
    if not worker_python_executable().is_file():
        raise VoxCpmLifecycleError(
            "VOXCPM_RUNTIME_NOT_INSTALLED",
            "VoxCPM2 worker environment does not exist yet.",
        )
    result = subprocess.run(
        [
            str(worker_python_executable()),
            "-c",
            "import voxcpm; print(voxcpm.__version__ if hasattr(voxcpm, '__version__') else 'ok')",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    ok = result.returncode == 0
    return {
        "provider_id": "voxcpm2",
        "ok": ok,
        "env_dir": str(worker_env_dir()),
        "version": (result.stdout or "").strip() or None,
        "error": None if ok else (result.stderr or result.stdout).strip()[-2000:],
    }


def install_runtime() -> dict[str, Any]:
    """Create the worker env and install the runtime into it (idempotent)."""
    from app.services.voxcpm_env import ensure_worker_env

    try:
        env_dir = ensure_worker_env()
    except VoxCpmEnvError as exc:
        raise VoxCpmLifecycleError(exc.code, exc.message) from exc
    return {
        "provider_id": "voxcpm2",
        "env_dir": str(env_dir),
        "installed": True,
    }


def _rmtree_best_effort(directory: Path) -> tuple[bool, str | None]:
    """rmtree that survives Windows file locks instead of raising a 500.

    Locked files (a running worker, an open HF blob handle) are removed on a
    retry; whatever still cannot be deleted is reported instead of failing.
    """
    try:
        shutil.rmtree(directory)
        return True, None
    except OSError as exc:
        # Retry once after a short pause: transient locks (AV scans, a worker
        # winding down) usually clear. Remaining locked entries stay behind.
        import time

        time.sleep(0.5)
        try:
            shutil.rmtree(directory, ignore_errors=False)
            return True, None
        except OSError as retry_exc:
            logger.warning("Partial removal of %s: %s", directory, retry_exc)
            if directory.is_dir():
                return False, str(retry_exc)[-500:]
            return True, None


def remove_installation() -> dict[str, Any]:
    """Remove the dedicated worker env. The HF model cache is reported but
    only removed when ``remove_model`` is also requested by the caller."""
    env_dir = worker_env_dir()
    removed = False
    error: str | None = None
    if env_dir.is_dir():
        removed, error = _rmtree_best_effort(env_dir)
    return {
        "provider_id": "voxcpm2",
        "env_removed": removed,
        "error": error,
        "model_cache_dir": str(_model_cache_dir()),
        "model_cache_present": _model_cache_dir().is_dir(),
    }


def remove_model_cache() -> dict[str, Any]:
    """Delete the downloaded HF model cache (frees ~4.6 GB)."""
    cache_dir = _model_cache_dir()
    removed = True
    error: str | None = None
    if cache_dir.is_dir():
        removed, error = _rmtree_best_effort(cache_dir)
    return {
        "provider_id": "voxcpm2",
        "model_removed": removed,
        "error": error,
        "freed_bytes": None,
    }


def get_runtime_state() -> dict[str, Any]:
    """Runtime-tab state: process/model/device — separate from installation."""
    installation = get_installation_status()
    return {
        "provider_id": "voxcpm2",
        "model_id": VOXCPM_MODEL_ID,
        "env_present": installation["env_present"],
        "package_installed": installation["package_installed"],
        "model_downloaded": installation["model_status"] == "downloaded",
        "downloaded_bytes": installation["downloaded_bytes"],
    }


def model_download_progress() -> dict[str, Any]:
    """Coarse download progress for Settings UI (bytes-based, no lock file)."""
    expected = 4_600_000_000  # ~4.6 GB checkpoint, reported by HF
    downloaded = _model_total_bytes()
    return {
        "provider_id": "voxcpm2",
        "model_id": VOXCPM_MODEL_ID,
        "downloaded_bytes": downloaded,
        "expected_bytes": expected,
        "complete": _model_snapshot_dir() is not None,
    }