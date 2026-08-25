"""Installer: staging → probe → atomic activation with rollback."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from app.services.runtime_manager.models import RuntimeManifest, RuntimeManagerError
from app.services.runtime_manager.verifier import safe_extract_zip

logger = logging.getLogger(__name__)


def runtime_base_dir(data_dir: Path, runtime_id: str | None = None) -> Path:
    base = data_dir / "runtimes"
    return base / runtime_id if runtime_id else base


def runtime_version_dir(data_dir: Path, runtime_id: str, version: str) -> Path:
    return runtime_base_dir(data_dir) / runtime_id / version


def staging_dir(data_dir: Path, runtime_id: str, version: str) -> Path:
    return runtime_base_dir(data_dir) / runtime_id / f"{version}.staging"


def active_symlink(data_dir: Path, runtime_id: str) -> Path:
    return runtime_base_dir(data_dir) / runtime_id / "active"


def install_pack(
    zip_path: Path,
    manifest: RuntimeManifest,
    data_dir: Path,
    *,
    probe_fn=None,
) -> Path:
    """Extract pack into staging, probe, then atomically activate.

    *probe_fn* is an optional callable(staging_entrypoint) -> dict. If it
    returns or raises, installation fails and staging is cleaned up.
    """
    rid = manifest.runtime_id
    version = manifest.version
    staging = staging_dir(data_dir, rid, version)

    # Clean any stale staging from a prior failed attempt.
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        safe_extract_zip(zip_path, staging)
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    # Write manifest alongside extracted files for later introspection.
    (staging / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2), encoding="utf-8"
    )

    entrypoint = staging / manifest.entrypoint
    if not entrypoint.is_file():
        shutil.rmtree(staging, ignore_errors=True)
        raise RuntimeManagerError(
            "ENTRYPOINT_MISSING",
            f"Entrypoint {manifest.entrypoint} not found after extraction.",
        )

    if probe_fn is not None:
        try:
            probe_fn(entrypoint)
        except Exception as exc:
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeManagerError(
                "PROBE_FAILED", f"Worker probe failed: {exc}"
            ) from exc

    final = runtime_version_dir(data_dir, rid, version)
    if final.exists():
        shutil.rmtree(final, ignore_errors=True)
    staging.rename(final)

    _activate(data_dir, rid, version)
    logger.info("runtime pack %s@%s installed → %s", rid, version, final)
    return final


def _activate(data_dir: Path, runtime_id: str, version: str) -> Path:
    """Point the 'active' symlink at the given version directory."""
    link = active_symlink(data_dir, runtime_id)
    target = runtime_version_dir(data_dir, runtime_id, version)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)
    return target


def rollback(data_dir: Path, runtime_id: str) -> str | None:
    """Revert to the previous installed version if one exists.

    Returns the version now active, or None if none available.
    """
    base = runtime_base_dir(data_dir, runtime_id)
    versions = sorted(
        [p.name for p in base.iterdir() if p.is_dir() and p.name not in ("active",)]
    )
    current_link = active_symlink(data_dir, runtime_id)
    current = current_link.resolve().name if current_link.is_symlink() else None
    remaining = [v for v in versions if v != current]
    if not remaining:
        return None
    prev = remaining[-1]
    _activate(data_dir, runtime_id, prev)
    logger.info("runtime %s rolled back to %s", runtime_id, prev)
    return prev


def uninstall_version(data_dir: Path, runtime_id: str, version: str) -> None:
    """Remove a specific version directory. Never remove the active version."""
    link = active_symlink(data_dir, runtime_id)
    active_target = link.resolve() if link.is_symlink() else None
    target = runtime_version_dir(data_dir, runtime_id, version)
    if active_target is not None and target.resolve() == active_target.resolve():
        raise RuntimeManagerError(
            "CANNOT_REMOVE_ACTIVE",
            "Uninstall the active version via deactivate or remove first.",
        )
    shutil.rmtree(target, ignore_errors=True)


def uninstall_runtime(data_dir: Path, runtime_id: str) -> None:
    """Remove the entire runtime pack (all versions + active pointer)."""
    base = runtime_base_dir(data_dir, runtime_id)
    shutil.rmtree(base, ignore_errors=True)


def disk_usage(data_dir: Path, runtime_id: str) -> int:
    """Total bytes on disk for the given runtime pack."""
    base = runtime_base_dir(data_dir, runtime_id)
    if not base.exists():
        return 0
    total = 0
    for p in base.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total