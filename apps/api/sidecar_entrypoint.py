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


def isolate_sidecar_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Return only values intentionally injected by the desktop runtime."""

    return {
        name: environ[name]
        for name in RUNTIME_ENVIRONMENT_NAMES
        if name in environ
    }


def main() -> None:
    runtime_environment = isolate_sidecar_environment(os.environ)
    os.environ.clear()
    os.environ.update(runtime_environment)
    runpy.run_module("app.main", run_name="__main__")


if __name__ == "__main__":
    main()
