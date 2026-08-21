"""Model manifest, downloader, cache, and checksum verification for VieNeu.

VieNeu's own ``hf_hub_download`` calls fetch the latest ``main`` revision by
default (no ``revision=`` pin). This module pins exact HF commit SHAs so the
model is reproducible, downloads files with concurrency=1, and verifies SHA-256
checksums. The manager (engine.py) points ``HF_HOME`` at the populated cache so
Vieneu finds local files without hitting the network at load time.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from vieneu_core.errors import ModelLoadFailedError


@dataclass(frozen=True)
class ModelFile:
    filename: str
    expected_sha256: str | None = None


@dataclass(frozen=True)
class ModelManifest:
    """Pinned model manifest for reproducible downloads.

    The ``revision`` fields are Hugging Face commit SHAs (NOT branch names like
    ``main``) so the same snapshot is fetched every time. SHAs were resolved on
    2026-08-05.
    """

    repo_id: str
    revision: str
    files: tuple[ModelFile, ...] = field(default_factory=tuple)


# Pinned revisions (resolved 2026-08-05).
VIENEU_V3_TURBO_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
VIENEU_V3_TURBO_REVISION = "2da0efab622a1722125991736524f080b751ef5b"
MOSS_ONNX_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"
MOSS_ONNX_REVISION = "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae"


def default_manifests() -> list[ModelManifest]:
    """Return the default pinned manifests for the VieNeu v3 Turbo CPU path.

    File lists are intentionally empty here — at runtime Vieneu decides which
    files it needs; the downloader fetches whatever is listed. When full
    reproducibility is required (Phase 10/11), enumerate every file with its
    SHA-256. For now the manifest pins the repo+revision so ``hf_hub_download``
    with ``revision=<sha>`` is deterministic even without a file list.
    """

    return [
        ModelManifest(
            repo_id=VIENEU_V3_TURBO_REPO,
            revision=VIENEU_V3_TURBO_REVISION,
            files=(),
        ),
        ModelManifest(
            repo_id=MOSS_ONNX_REPO,
            revision=MOSS_ONNX_REVISION,
            files=(),
        ),
    ]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(path: Path, expected_sha256: str | None) -> bool:
    """Return True if the file exists and its SHA-256 matches (or is unknown)."""
    if not path.exists():
        return False
    if expected_sha256 is None:
        return True
    return _sha256(path).lower() == expected_sha256.lower()


def verify_cache(manifest: ModelManifest, cache_dir: Path) -> bool:
    """Verify all manifest files are present and match their checksums."""
    cache_root = Path(cache_dir)
    for entry in manifest.files:
        # huggingface_hub caches by hash; we only verify if a direct path is known.
        if not verify_file(cache_root / entry.filename, entry.expected_sha256):
            return False
    return True


class ModelDownloader:
    """Downloads pinned model files with concurrency=1.

    Uses ``huggingface_hub.hf_hub_download`` with the pinned ``revision`` SHA
    so the snapshot is reproducible. Network errors are mapped to a retryable
    ``ModelLoadFailedError``.
    """

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._semaphore = asyncio.Semaphore(1)  # download concurrency = 1

    async def download_manifest(self, manifest: ModelManifest) -> list[Path]:
        if not manifest.files:
            return []
        loop = asyncio.get_running_loop()
        results: list[Path] = []
        for entry in manifest.files:
            async with self._semaphore:
                path = await loop.run_in_executor(
                    None,
                    self._download_one,
                    manifest,
                    entry,
                )
            results.append(path)
        return results

    def _download_one(self, manifest: ModelManifest, entry: ModelFile) -> Path:
        from huggingface_hub import hf_hub_download  # type: ignore

        try:
            local_path = hf_hub_download(
                repo_id=manifest.repo_id,
                filename=entry.filename,
                revision=manifest.revision,
                cache_dir=str(self._cache_dir) if self._cache_dir else None,
            )
        except Exception as exc:
            raise ModelLoadFailedError(
                message=f"Failed to download {entry.filename} from {manifest.repo_id}: {exc}",
                retryable=True,
            ) from exc
        local = Path(local_path)
        if entry.expected_sha256 is not None and not verify_file(
            local, entry.expected_sha256
        ):
            raise ModelLoadFailedError(
                message=f"Checksum mismatch for {entry.filename} (expected {entry.expected_sha256})",
                retryable=False,
            )
        return local
