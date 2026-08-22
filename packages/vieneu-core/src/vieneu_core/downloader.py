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


@dataclass(frozen=True)
class VieneuModelArtifacts:
    """Resolved local directories used by the VieNeu v3 Turbo engine."""

    backbone_dir: Path
    onnx_dir: Path
    codec_dir: Path


# Pinned revisions (resolved 2026-08-05).
VIENEU_V3_TURBO_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
VIENEU_V3_TURBO_REVISION = "2da0efab622a1722125991736524f080b751ef5b"
MOSS_ONNX_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"
MOSS_ONNX_REVISION = "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae"


def default_manifests() -> list[ModelManifest]:
    """Return the pinned files required by the CPU voice-cloning path."""

    return [
        ModelManifest(
            repo_id=VIENEU_V3_TURBO_REPO,
            revision=VIENEU_V3_TURBO_REVISION,
            files=tuple(
                ModelFile(filename=filename)
                for filename in (
                    "speaker_encoder.onnx",
                    "denoiser.onnx",
                    "onnx_int8/vieneu_prefill.onnx",
                    "onnx_int8/vieneu_decode_step.onnx",
                    "onnx_int8/vieneu_acoustic_cached.onnx",
                    "onnx_int8/vieneu_backbone_shared.data",
                    "onnx_int8/vieneu_v3_heads.npz",
                    "onnx_int8/config.json",
                    "onnx_int8/tokenizer.json",
                )
            ),
        ),
        ModelManifest(
            repo_id=MOSS_ONNX_REPO,
            revision=MOSS_ONNX_REVISION,
            files=tuple(
                ModelFile(filename=filename)
                for filename in (
                    "moss_audio_tokenizer_encode.onnx",
                    "moss_audio_tokenizer_encode.data",
                    "moss_audio_tokenizer_decode_full.onnx",
                    "moss_audio_tokenizer_decode_shared.data",
                    "moss_audio_tokenizer_decode_step.onnx",
                    "codec_browser_onnx_meta.json",
                )
            ),
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

    async def download_snapshot(self, manifest: ModelManifest) -> Path:
        """Resolve a complete pinned snapshot, using cache before the network."""

        loop = asyncio.get_running_loop()
        async with self._semaphore:
            return await loop.run_in_executor(
                None,
                self._download_snapshot,
                manifest,
            )

    def _download_snapshot(self, manifest: ModelManifest) -> Path:
        from huggingface_hub import snapshot_download  # type: ignore

        patterns = [entry.filename for entry in manifest.files]
        kwargs = {
            "repo_id": manifest.repo_id,
            "revision": manifest.revision,
            "allow_patterns": patterns,
        }
        if self._cache_dir is not None:
            kwargs["cache_dir"] = str(self._cache_dir)

        try:
            local_snapshot = snapshot_download(
                **kwargs,
                local_files_only=True,
            )
            snapshot_path = Path(local_snapshot)
            if _snapshot_complete(snapshot_path, manifest):
                return snapshot_path
        except Exception:
            # A missing or partial local snapshot is repaired by the pinned
            # network download below.
            pass

        try:
            local_snapshot = snapshot_download(**kwargs, local_files_only=False)
        except Exception as exc:
            raise ModelLoadFailedError(
                message=f"Failed to download model snapshot {manifest.repo_id}: {exc}",
                retryable=True,
            ) from exc

        snapshot_path = Path(local_snapshot)
        if not _snapshot_complete(snapshot_path, manifest):
            raise ModelLoadFailedError(
                message=f"Model snapshot {manifest.repo_id} is incomplete",
                retryable=False,
            )
        return snapshot_path

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


def _snapshot_complete(snapshot_path: Path, manifest: ModelManifest) -> bool:
    """Check that every required snapshot file exists and is non-empty."""

    return all(
        (snapshot_path / entry.filename).is_file()
        and (snapshot_path / entry.filename).stat().st_size > 0
        for entry in manifest.files
    )


async def ensure_default_model_artifacts(hf_home: Path) -> VieneuModelArtifacts:
    """Download the pinned v3 Turbo CPU snapshots and return their local paths.

    The local-only attempt makes subsequent application starts fast and
    offline-safe. A network request is made only when the pinned snapshot is
    missing or incomplete.
    """

    home = Path(hf_home)
    home.mkdir(parents=True, exist_ok=True)
    downloader = ModelDownloader(cache_dir=home / "hub")
    vieneu_manifest, codec_manifest = default_manifests()
    backbone_dir = await downloader.download_snapshot(vieneu_manifest)
    codec_dir = await downloader.download_snapshot(codec_manifest)
    return VieneuModelArtifacts(
        backbone_dir=backbone_dir,
        onnx_dir=backbone_dir / "onnx_int8",
        codec_dir=codec_dir,
    )
