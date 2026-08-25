"""SHA-256 verifier + safe ZIP extraction (rejects path traversal)."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from app.services.runtime_manager.models import RuntimeManagerError


def verify_sha256(path: Path, expected: str) -> bool:
    """Return True iff the file at *path* hashes to *expected* SHA-256 hex."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest() == expected


def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    """Extract a ZIP into *dest* rejecting absolute/`..` traversal entries.

    Every member must resolve inside *dest* after symlinks are resolved.
    Raises RuntimeManagerError on any unsafe or unexpected entry.
    """
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            # Skip directory entries — created implicitly on file extraction.
            if info.is_dir():
                continue
            member_path = info.filename
            if member_path.startswith(("/", "\\")) or ".." in Path(member_path).parts:
                raise RuntimeManagerError(
                    "UNSAFE_ZIP_ENTRY",
                    f"Refusing to extract unsafe zip entry: {member_path}",
                )
            target = (dest / member_path).resolve()
            try:
                target.relative_to(dest)
            except ValueError:
                raise RuntimeManagerError(
                    "UNSAFE_ZIP_ENTRY",
                    f"Resolved path escapes destination: {member_path}",
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, open(target, "wb") as dst:
                while chunk := src.read(65536):
                    dst.write(chunk)