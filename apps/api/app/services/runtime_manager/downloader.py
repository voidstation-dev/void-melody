"""Verified runtime pack downloader with progress reporting."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from app.services.runtime_manager.models import RuntimeManagerError
from app.services.runtime_manager.verifier import verify_sha256

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float], None]


def download_runtime_pack(
    url: str,
    dest: Path,
    *,
    expected_sha256: str,
    on_progress: ProgressFn | None = None,
    timeout: float = 120.0,
) -> Path:
    """Download *url* to *dest*, verify SHA-256, raise on mismatch.

    Writes to a .partial sibling first, then atomically renames to *dest*
    only after verification passes.
    """
    if not url:
        raise RuntimeManagerError("NO_DOWNLOAD_URL", "Manifest has no download URL.")

    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")

    try:
        req = Request(url, headers={"User-Agent": "VoidMelody-RuntimeManager"})
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL from trusted manifest
            total = int(resp.headers.get("Content-Length", "0"))
            downloaded = 0
            with open(partial, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and on_progress is not None:
                        on_progress(downloaded / total)
    except Exception as exc:
        partial.unlink(missing_ok=True)
        raise RuntimeManagerError("DOWNLOAD_FAILED", str(exc)) from exc

    if expected_sha256 and not verify_sha256(partial, expected_sha256):
        partial.unlink(missing_ok=True)
        raise RuntimeManagerError("CHECKSUM_MISMATCH", "Downloaded pack failed SHA-256 verification.")

    partial.replace(dest)
    if on_progress is not None:
        on_progress(1.0)
    logger.info("runtime pack downloaded to %s", dest)
    return dest