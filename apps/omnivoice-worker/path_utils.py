"""Path validation utilities for OmniVoice worker security."""

from __future__ import annotations

import os
from pathlib import Path

from errors import (
    OMNI_ALLOWED_ROOTS_NOT_CONFIGURED,
    OMNI_INVALID_PARAMS,
    OMNI_PATH_OUTSIDE_ROOT,
    WorkerError,
)


def get_allowed_roots() -> list[Path]:
    """Return list of allowed root directories from environment or defaults."""
    env_roots = os.environ.get("VOID_OMNI_ALLOWED_ROOTS")
    if env_roots:
        separator = ";" if os.name == "nt" else ":"
        if ";" in env_roots:
            separator = ";"
        elif "," in env_roots:
            separator = ","
        return [Path(p.strip()).resolve() for p in env_roots.split(separator) if p.strip()]

    return []


def validate_path(
    path_str: str,
    *,
    must_exist: bool = False,
    param_name: str = "path",
    require_roots: bool = True,
) -> Path:
    """Resolve and validate that a path is within allowed root directories."""
    if not path_str or not isinstance(path_str, str):
        raise WorkerError(OMNI_INVALID_PARAMS, f"Parameter '{param_name}' must be a non-empty string")

    try:
        resolved = Path(path_str).resolve()
    except Exception as exc:
        raise WorkerError(OMNI_INVALID_PARAMS, f"Invalid path for '{param_name}': {exc}") from exc

    allowed_roots = get_allowed_roots()
    if not allowed_roots:
        # In non-mock mode, failing open is unsafe. Fail closed.
        if require_roots and os.environ.get("OMNIVOICE_WORKER_MODE") != "mock":
            raise WorkerError(
                OMNI_ALLOWED_ROOTS_NOT_CONFIGURED,
                "Worker filesystem access rejected: VOID_OMNI_ALLOWED_ROOTS is not configured.",
            )
    else:
        is_allowed = False
        for root in allowed_roots:
            try:
                resolved.relative_to(root)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            raise WorkerError(
                OMNI_PATH_OUTSIDE_ROOT,
                f"Path '{path_str}' is outside allowed root directories",
            )

    if must_exist and not resolved.exists():
        raise WorkerError(OMNI_INVALID_PARAMS, f"Path '{path_str}' does not exist")

    return resolved
