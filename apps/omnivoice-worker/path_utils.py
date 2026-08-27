"""Filesystem path validation for the OmniVoice worker."""

from __future__ import annotations

import os
from pathlib import Path

from errors import (
    OMNI_ALLOWED_ROOTS_NOT_CONFIGURED,
    OMNI_PATH_OUTSIDE_ROOT,
    WorkerError,
)


def _allowed_roots() -> list[Path]:
    raw = os.environ.get("VOID_OMNI_ALLOWED_ROOTS", "")
    if not raw:
        return []
    return [Path(p).resolve() for p in raw.split(os.pathsep) if p.strip()]


def validate_path(path_str: str) -> Path:
    """Resolve *path_str* and ensure it stays under an allowed root.

    Raises:
        WorkerError: if allowed roots are not configured or the path escapes.
    """
    roots = _allowed_roots()
    if not roots:
        raise WorkerError(
            OMNI_ALLOWED_ROOTS_NOT_CONFIGURED,
            "VOID_OMNI_ALLOWED_ROOTS is not configured.",
        )

    target = Path(path_str).resolve()
    for root in roots:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue

    raise WorkerError(
        OMNI_PATH_OUTSIDE_ROOT,
        f"Path '{path_str}' is outside allowed roots.",
    )


def validate_path_or_mock(path_str: str) -> Path:
    """Resolve *path_str* for mock mode.

    If allowed roots are configured, enforce them. Otherwise accept any path so
    mock mode works out of the box in tests and development.
    """
    roots = _allowed_roots()
    target = Path(path_str).resolve()
    if not roots:
        return target

    for root in roots:
        try:
            target.relative_to(root)
            return target
        except ValueError:
            continue

    raise WorkerError(
        OMNI_PATH_OUTSIDE_ROOT,
        f"Path '{path_str}' is outside allowed roots.",
    )
