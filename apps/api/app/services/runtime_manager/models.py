"""Runtime pack data models and manifest schema."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RuntimeStatus(str, Enum):
    missing = "missing"
    downloading = "downloading"
    verifying = "verifying"
    installing = "installing"
    ready = "ready"
    error = "error"
    update_required = "update_required"


KNOWN_RUNTIME_IDS = ("vieneu", "speech", "omnivoice")
PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class RuntimeManifest:
    """Describes a downloadable runtime pack. Verified before extraction."""

    schema_version: int
    runtime_id: str
    version: str
    protocol_version: int
    platform: str  # "windows" | "linux" | "macos"
    arch: str  # "x86_64" | "aarch64"
    download_url: str
    sha256: str
    size_bytes: int
    entrypoint: str
    minimum_app_version: str | None = None
    maximum_app_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "id": self.runtime_id,
            "version": self.version,
            "protocolVersion": self.protocol_version,
            "platform": self.platform,
            "arch": self.arch,
            "downloadUrl": self.download_url,
            "sha256": self.sha256,
            "sizeBytes": self.size_bytes,
            "entrypoint": self.entrypoint,
            "minimumAppVersion": self.minimum_app_version,
            "maximumAppVersion": self.maximum_app_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeManifest:
        return cls(
            schema_version=int(data["schemaVersion"]),
            runtime_id=str(data["id"]),
            version=str(data["version"]),
            protocol_version=int(data["protocolVersion"]),
            platform=str(data["platform"]),
            arch=str(data["arch"]),
            download_url=str(data["downloadUrl"]),
            sha256=str(data["sha256"]),
            size_bytes=int(data["sizeBytes"]),
            entrypoint=str(data["entrypoint"]),
            minimum_app_version=data.get("minimumAppVersion"),
            maximum_app_version=data.get("maximumAppVersion"),
        )


@dataclass
class RuntimeState:
    """In-memory status of one runtime pack."""

    runtime_id: str
    status: RuntimeStatus = RuntimeStatus.missing
    active_version: str | None = None
    installed_versions: list[str] = None  # type: ignore[assignment]
    disk_usage_bytes: int = 0
    progress: float = 0.0  # 0..1 during download
    error: str | None = None
    protocol_version: int | None = None
    probe_result: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.installed_versions is None:
            self.installed_versions = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.runtime_id,
            "status": self.status.value,
            "activeVersion": self.active_version,
            "installedVersions": list(self.installed_versions),
            "diskUsageBytes": self.disk_usage_bytes,
            "progress": round(self.progress, 3),
            "error": self.error,
            "protocolVersion": self.protocol_version,
            "probeResult": self.probe_result,
        }


class RuntimeManagerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message