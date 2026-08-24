"""Conservative startup cleanup and deletion for Voice Lab artifacts."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

_PROFILE_FILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(?:wav|mp3|m4a)$",
    re.IGNORECASE,
)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def delete_voice_profile_directory(voice_id: str, voice_dir: Path) -> None:
    """Safely delete an entire voice profile directory and legacy top-level audio files."""
    if not voice_id or not _UUID_PATTERN.fullmatch(voice_id):
        return

    profile_dir = voice_dir / voice_id
    if profile_dir.is_dir():
        shutil.rmtree(profile_dir, ignore_errors=True)

    # Clean legacy v1 top-level files if present
    for ext in (".wav", ".mp3", ".m4a"):
        legacy_file = voice_dir / f"{voice_id}{ext}"
        if legacy_file.is_file():
            legacy_file.unlink(missing_ok=True)


def cleanup_orphan_voice_artifacts(
    voice_dir: Path,
    *,
    known_paths: set[Path],
    known_voice_ids: set[str] | None = None,
    older_than_seconds: float = 3_600,
    now: float | None = None,
) -> list[Path]:
    """Remove stale UUID profile directories, files, and temporary upload/analysis files.

    Final files referenced by the database are always preserved.
    """
    if not voice_dir.exists():
        return []
    current_time = time.time() if now is None else now
    resolved_known = {path.resolve() for path in known_paths}
    known_ids = known_voice_ids or set()
    removed: list[Path] = []

    for path in voice_dir.iterdir():
        if path.is_file() and _PROFILE_FILE.fullmatch(path.name):
            try:
                if path.resolve() in resolved_known:
                    continue
                if current_time - path.stat().st_mtime <= older_than_seconds:
                    continue
                path.unlink()
                removed.append(path)
            except (FileNotFoundError, OSError):
                continue
        elif path.is_dir() and _UUID_PATTERN.fullmatch(path.name):
            try:
                if path.name in known_ids or path.resolve() in resolved_known:
                    continue
                if current_time - path.stat().st_mtime <= older_than_seconds:
                    continue
                shutil.rmtree(path, ignore_errors=True)
                removed.append(path)
            except (FileNotFoundError, OSError):
                continue

    for directory_name in (".analysis", ".uploads"):
        directory = voice_dir / directory_name
        if directory.is_dir():
            for path in directory.rglob("*"):
                if path.is_file():
                    try:
                        if path.resolve() in resolved_known:
                            continue
                        if current_time - path.stat().st_mtime <= older_than_seconds:
                            continue
                        path.unlink()
                        removed.append(path)
                    except (FileNotFoundError, OSError):
                        continue

    return removed
