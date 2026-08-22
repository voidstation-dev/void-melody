"""Start the packaged API with only the desktop runtime environment."""

from __future__ import annotations

import os
import runpy
from collections.abc import Mapping


RUNTIME_ENVIRONMENT_NAMES = frozenset(
    {
        "PYTHONUNBUFFERED",
        "APP_ENV",
        "API_HOST",
        "API_PORT",
        "MELODY_API_TOKEN",
        "MELODY_DATA_DIR",
        "MELODY_CATALOG_PATH",
        "VIENEU_HF_HOME",
        "HF_HOME",
        "TTS_APPLY_RATE_WITH_FFMPEG",
        "TTS_QUEUE_CONCURRENCY",
        "TTS_CHUNK_CONCURRENCY",
    }
)

PYINSTALLER_RUNTIME_ENVIRONMENT_NAMES = frozenset(
    {
        # PyInstaller uses this to make a one-file child a fresh application
        # instance instead of reusing the current extraction directory.
        "PYINSTALLER_RESET_ENVIRONMENT",
    }
)

OS_RUNTIME_ENVIRONMENT_NAMES = frozenset(
    {
        # Needed to locate executables and create temporary files on macOS and
        # Windows. HOME and USERPROFILE are used by their respective platforms.
        "PATH",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        # Windows requires its system directory for process startup. COMSPEC
        # and PATHEXT keep command and executable resolution intact.
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
    }
)


def _is_preserved_environment_name(name: str) -> bool:
    normalized_name = name.upper()
    return (
        name in RUNTIME_ENVIRONMENT_NAMES
        or normalized_name.startswith("_PYI_")
        or normalized_name in PYINSTALLER_RUNTIME_ENVIRONMENT_NAMES
        or normalized_name in OS_RUNTIME_ENVIRONMENT_NAMES
    )


def isolate_sidecar_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Return the desktop contract and safe PyInstaller/OS runtime state."""

    return {
        name: value
        for name, value in environ.items()
        if _is_preserved_environment_name(name)
    }


def main() -> None:
    runtime_environment = isolate_sidecar_environment(os.environ)
    os.environ.clear()
    os.environ.update(runtime_environment)
    runpy.run_module("app.main", run_name="__main__")


if __name__ == "__main__":
    main()
