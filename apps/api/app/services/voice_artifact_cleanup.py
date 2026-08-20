"""Conservative startup cleanup for Voice Lab artifacts."""

from __future__ import annotations

import re
import time
from pathlib import Path

_PROFILE_FILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(?:wav|mp3|m4a)$",
    re.IGNORECASE,
)


def cleanup_orphan_voice_artifacts(
    voice_dir: Path,
    *,
    known_paths: set[Path],
    older_than_seconds: float = 3_600,
    now: float | None = None,
) -> list[Path]:
    """Remove stale UUID profile files and temporary upload/analysis files.

    Only the known Voice Lab directories and UUID-named profile files are
    considered. Final files referenced by the database are always preserved.
    """

    if not voice_dir.exists():
        return []
    current_time = time.time() if now is None else now
    resolved_known = {path.resolve() for path in known_paths}
    candidates: list[Path] = []

    for path in voice_dir.iterdir():
        if path.is_file() and _PROFILE_FILE.fullmatch(path.name):
            candidates.append(path)

    for directory_name in (".analysis", ".uploads"):
        directory = voice_dir / directory_name
        if directory.is_dir():
            candidates.extend(path for path in directory.rglob("*") if path.is_file())

    removed: list[Path] = []
    for path in candidates:
        try:
            if path.resolve() in resolved_known:
                continue
            if current_time - path.stat().st_mtime <= older_than_seconds:
                continue
            path.unlink()
        except (FileNotFoundError, OSError):
            continue
        removed.append(path)
    return removed
