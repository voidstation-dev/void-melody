"""Persistent registry of installed runtime state (JSON on disk)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock

from app.services.runtime_manager.models import RuntimeState, RuntimeStatus

logger = logging.getLogger(__name__)
_REGISTRY_FILE = "runtime_registry.json"


def _registry_path(data_dir: Path) -> Path:
    return data_dir / _REGISTRY_FILE


class RuntimeRegistry:
    """Thread-safe JSON-backed registry of installed runtimes."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = Lock()
        self._state: dict[str, RuntimeState] = {}
        self._load()

    def _load(self) -> None:
        path = _registry_path(self._data_dir)
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("runtime registry corrupted, resetting")
            return
        for rid, entry in raw.items():
            self._state[rid] = RuntimeState(
                runtime_id=rid,
                status=RuntimeStatus(entry.get("status", "missing")),
                active_version=entry.get("activeVersion"),
                installed_versions=entry.get("installedVersions", []),
                disk_usage_bytes=entry.get("diskUsageBytes", 0),
                protocol_version=entry.get("protocolVersion"),
                error=entry.get("error"),
            )

    def _save(self) -> None:
        path = _registry_path(self._data_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {rid: s.to_dict() for rid, s in self._state.items()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self, runtime_id: str) -> RuntimeState:
        with self._lock:
            return self._state.get(
                runtime_id, RuntimeState(runtime_id=runtime_id)
            )

    def list_all(self) -> list[RuntimeState]:
        with self._lock:
            return list(self._state.values())

    def update(self, runtime_id: str, **changes) -> RuntimeState:
        with self._lock:
            state = self._state.get(runtime_id, RuntimeState(runtime_id=runtime_id))
            for key, value in changes.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            self._state[runtime_id] = state
            self._save()
            return state

    def set_status(
        self, runtime_id: str, status: RuntimeStatus, error: str | None = None
    ) -> RuntimeState:
        return self.update(runtime_id, status=status, error=error)

    def set_active(
        self, runtime_id: str, version: str, protocol_version: int | None = None
    ) -> RuntimeState:
        with self._lock:
            state = self._state.get(runtime_id, RuntimeState(runtime_id=runtime_id))
            state.active_version = version
            if protocol_version is not None:
                state.protocol_version = protocol_version
            if version not in state.installed_versions:
                state.installed_versions.append(version)
            state.installed_versions.sort()
            state.status = RuntimeStatus.ready
            state.error = None
            self._state[runtime_id] = state
            self._save()
            return state

    def clear(self, runtime_id: str) -> RuntimeState:
        return self.update(
            runtime_id,
            status=RuntimeStatus.missing,
            active_version=None,
            installed_versions=[],
            disk_usage_bytes=0,
            protocol_version=None,
            probe_result=None,
            error=None,
        )