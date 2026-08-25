"""RuntimeManagerService — orchestrates install/update/repair/remove/status."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.config import settings
from app.services.runtime_manager.installer import (
    disk_usage,
    install_pack,
    rollback,
    runtime_base_dir,
    runtime_version_dir,
    uninstall_runtime,
    uninstall_version,
)
from app.services.runtime_manager.models import (
    PROTOCOL_VERSION,
    RuntimeManagerError,
    RuntimeState,
    RuntimeStatus,
)
from app.services.runtime_manager.registry import RuntimeRegistry
from app.services.runtime_manager.manifests import (
    get_manifest,
    is_known_runtime,
)

logger = logging.getLogger(__name__)


class RuntimeManagerService:
    """Single shared runtime manager for all packs."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or Path(settings.custom_voices_dir).parent
        self._registry = RuntimeRegistry(self._data_dir)

    # ---- status ----

    def status(self, runtime_id: str) -> RuntimeState:
        if not is_known_runtime(runtime_id):
            raise RuntimeManagerError("UNKNOWN_RUNTIME", f"Unknown runtime id: {runtime_id}")
        state = self._registry.get(runtime_id)
        state.disk_usage_bytes = disk_usage(self._data_dir, runtime_id)
        return state

    def list_statuses(self) -> list[RuntimeState]:
        return [self.status(rid) for rid in ("vieneu", "speech")]

    # ---- install ----

    def install(
        self,
        runtime_id: str,
        *,
        zip_path: Path | None = None,
        on_progress=None,
    ) -> RuntimeState:
        """Install a runtime pack.

        If *zip_path* is provided (already downloaded), use it directly.
        Otherwise this would download from the manifest URL — but current
        manifests have no download URL, so callers must supply a zip.
        """
        manifest = get_manifest(runtime_id)
        if manifest is None:
            raise RuntimeManagerError("UNKNOWN_RUNTIME", f"Unknown runtime id: {runtime_id}")
        if zip_path is None:
            raise RuntimeManagerError(
                "NO_DOWNLOAD_URL",
                "Runtime manifests have no download URL yet; supply a local zip_path.",
            )

        self._registry.set_status(runtime_id, RuntimeStatus.installing)
        try:
            final_dir = install_pack(zip_path, manifest, self._data_dir)
            self._registry.set_active(
                runtime_id,
                manifest.version,
                protocol_version=manifest.protocol_version,
            )
            self._registry.update(
                runtime_id, disk_usage_bytes=disk_usage(self._data_dir, runtime_id)
            )
        except Exception as exc:
            self._registry.set_status(runtime_id, RuntimeStatus.error, str(exc))
            raise
        return self.status(runtime_id)

    # ---- update ----

    def update(
        self,
        runtime_id: str,
        *,
        zip_path: Path,
    ) -> RuntimeState:
        """Install a new version over the existing one (keeps old for rollback)."""
        return self.install(runtime_id, zip_path=zip_path)

    # ---- repair ----

    def repair(self, runtime_id: str) -> RuntimeState:
        """Re-probe the active runtime entrypoint.

        If the worker probe passes, mark ready. If it fails, mark error /
        update_required depending on protocol compatibility.
        """
        state = self.status(runtime_id)
        if state.active_version is None:
            return state
        entrypoint = self._active_entrypoint(runtime_id)
        if entrypoint is None or not entrypoint.is_file():
            return self._registry.set_status(
                runtime_id, RuntimeStatus.error, "Entrypoint missing"
            )
        # Probe is a no-op for now (no worker protocol wired); mark ready.
        self._registry.set_status(runtime_id, RuntimeStatus.ready)
        return self.status(runtime_id)

    # ---- remove ----

    def remove(self, runtime_id: str) -> None:
        uninstall_runtime(self._data_dir, runtime_id)
        self._registry.clear(runtime_id)

    # ---- rollback ----

    def rollback(self, runtime_id: str) -> RuntimeState:
        prev = rollback(self._data_dir, runtime_id)
        if prev is None:
            return self.status(runtime_id)
        return self._registry.set_active(runtime_id, prev)

    # ---- helpers ----

    def _active_entrypoint(self, runtime_id: str) -> Path | None:
        state = self._registry.get(runtime_id)
        if state.active_version is None:
            return None
        manifest = get_manifest(runtime_id)
        if manifest is None:
            return None
        return runtime_version_dir(self._data_dir, runtime_id, state.active_version) / manifest.entrypoint

    @property
    def data_dir(self) -> Path:
        return self._data_dir


# Singleton for API reuse.
runtime_manager = RuntimeManagerService()