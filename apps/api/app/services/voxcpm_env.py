"""VoxCPM2 worker environment bootstrap.

Phase 4: the real voxcpm package requires Python >=3.10,<3.13 + torch >=2.5,
which is incompatible with the FastAPI main environment. The worker therefore
runs in a dedicated Python environment managed under the app data dir
(``data/envs/voxcpm``), created lazily with ``uv`` (or ``python -m venv`` as
fallback) and never installed into the FastAPI main environment.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from app.config import _data_dir

logger = logging.getLogger(__name__)

VOXCPM_WORKER_ENV_ID = "voxcpm"
VOXCPM_PYTHON_MAX_MINOR = 12  # voxcpm requires Python <3.13

VOXCPM_INSTALL_MARKER = "voxcpm-runtime.installed"


def _worker_source_dir() -> Path:
    """Directory holding the worker package (worker.py, pyproject.toml).

    Dev: apps/voxcpm-worker relative to the repo root. Frozen (PyInstaller
    onefile): the worker sources ride along as --add-data under
    ``voxcpm-worker/`` next to the bundle root, so resolve from the bundle
    dir (``sys._MEIPASS``) instead of ``__file__`` (which lives in the temp
    extraction dir and has no repo structure above it).
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass) / "voxcpm-worker"
            if bundled.is_dir():
                return bundled
    return Path(__file__).resolve().parents[4] / "apps" / "voxcpm-worker"


class VoxCpmEnvError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def worker_env_dir() -> Path:
    """Directory of the dedicated worker environment."""
    return _data_dir / "envs" / VOXCPM_WORKER_ENV_ID


def worker_python_executable() -> Path:
    env_dir = worker_env_dir()
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def _main_python_is_compatible() -> bool:
    """The FastAPI interpreter must never be used to host the worker env."""
    return sys.version_info < (3, 13)


def env_exists() -> bool:
    return worker_python_executable().is_file()


def runtime_installed() -> bool:
    """True when the dedicated env exists and its marker file is present."""
    return env_exists() and (worker_env_dir() / VOXCPM_INSTALL_MARKER).is_file()


def _uv_executable() -> str | None:
    from shutil import which

    return which("uv")


def _find_compatible_python() -> str | None:
    """Find a Python >=3.10,<3.13 suitable for creating the worker venv.

    Preference order:
    1. VOID_VOXCPM_PYTHON override (absolute path to an interpreter)
    2. existing dedicated env (no-op)
    3. a system interpreter discovered via the `py` launcher or PATH
    4. uv-managed interpreters via `uv python list`
    """
    override = os.environ.get("VOID_VOXCPM_PYTHON")
    if override and Path(override).is_file():
        return override

    if env_exists():
        return str(worker_python_executable())

    # Without uv, a packaged machine has no interpreter hint at all: the
    # sidecar's own python is 3.14 (frozen) and unusable. Scan the `py`
    # launcher and PATH for a compatible one so the venv fallback works.
    from shutil import which

    py_launcher = which("py")
    if py_launcher:
        for minor in (12, 11, 10):
            probe = subprocess.run(
                [py_launcher, f"-3.{minor}", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                check=False,
            )
            if probe.returncode == 0 and probe.stdout.strip():
                return probe.stdout.strip()

    for minor in (12, 11, 10):
        candidate = which(f"python3.{minor}")
        if candidate:
            return candidate

    return None  # uv resolves interpreters itself via `uv venv --python`


def create_worker_env() -> Path:
    """Create the dedicated worker venv (idempotent). Returns env dir."""
    import venv as _venv

    env_dir = worker_env_dir()
    if env_exists():
        return env_dir

    env_dir.parent.mkdir(parents=True, exist_ok=True)
    spec_python = _find_compatible_python()

    uv_path = _uv_executable()
    if uv_path and spec_python:
        # --seed: uv venvs have no pip by default, and install_runtime drives
        # pip through the env's own interpreter — seed it or the install
        # step fails on every fresh uv-created env.
        command = [uv_path, "venv", "--seed", "--python", spec_python, str(env_dir)]
    elif uv_path:
        # uv fetches a suitable managed interpreter (>=3.10,<3.13) itself.
        uv_version = os.environ.get("VOID_VOXCPM_UV_PYTHON", "3.12")
        command = [uv_path, "venv", "--seed", "--python", uv_version, str(env_dir)]
    elif spec_python:
        command = [spec_python, "-m", "venv", str(env_dir)]
    else:
        raise VoxCpmEnvError(
            "VOXCPM_ENV_NO_COMPATIBLE_PYTHON",
            "No Python >=3.10,<3.13 available to create the VoxCPM2 worker "
            "environment. Install `uv` or set VOID_VOXCPM_PYTHON.",
        )

    logger.info("Creating VoxCPM2 worker env: %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not env_exists():
        raise VoxCpmEnvError(
            "VOXCPM_ENV_CREATE_FAILED",
            f"Failed to create worker env: {result.stderr.strip() or result.stdout.strip()}",
        )
    return env_dir


def install_runtime(env_dir: Path | None = None) -> Path:
    """Install voxcpm + torch into the dedicated env (idempotent via marker).

    Never runs in the FastAPI main environment: every pip invocation targets
    the dedicated env's interpreter with its own site-packages.
    """
    env_dir = env_dir or create_worker_env()
    python = worker_python_executable() if env_dir == worker_env_dir() else (
        env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not python.is_file():
        raise VoxCpmEnvError(
            "VOXCPM_ENV_CREATE_FAILED",
            f"Worker env python not found at {python}",
        )

    if runtime_installed() and env_dir == worker_env_dir():
        return env_dir

    command = [
        str(python),
        "-m",
        "pip",
        # pip requires --python before the subcommand.
        "--python",
        str(python),
        "install",
        ".[runtime]",
    ]
    # Run pip from the worker directory so `.[runtime]` resolves.
    worker_dir = _worker_source_dir()
    logger.info("Installing VoxCPM2 runtime into %s", env_dir)
    result = subprocess.run(
        command,
        cwd=str(worker_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise VoxCpmEnvError(
            "VOXCPM_RUNTIME_INSTALL_FAILED",
            f"voxcpm runtime install failed: {result.stderr.strip() or result.stdout.strip()}",
        )
    if env_dir == worker_env_dir():
        (worker_env_dir() / VOXCPM_INSTALL_MARKER).write_text("ok", encoding="utf-8")
    return env_dir


def ensure_worker_env() -> Path:
    """Create env + install runtime if missing. Returns env dir."""
    env_dir = create_worker_env()
    install_runtime(env_dir)
    return env_dir


def worker_python_args(mock_mode: bool = False) -> list[str]:
    """argv prefix for spawning the worker in the dedicated env."""
    python = worker_python_executable()
    if not python.is_file():
        raise VoxCpmEnvError(
            "VOXCPM_RUNTIME_NOT_INSTALLED",
            f"VoxCPM2 worker env not found at {worker_env_dir()}",
        )
    worker_script = _worker_source_dir() / "worker.py"
    args = [str(python), str(worker_script)]
    if mock_mode:
        args.append("--mock")
    return args