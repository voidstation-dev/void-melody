"""Manifest registry — known runtime manifests and platform detection.

In a production deployment these would be fetched from a trusted manifest
server over HTTPS. For now we ship a local registry that the app can probe
and from which installs can be initiated once download URLs are populated.
"""

from __future__ import annotations

import platform as _platform
import sys

from app.services.runtime_manager.models import (
    KNOWN_RUNTIME_IDS,
    PROTOCOL_VERSION,
    RuntimeManifest,
)

_CURRENT_PLATFORM = {
    "Windows": "windows",
    "Linux": "linux",
    "Darwin": "macos",
}.get(_platform.system(), "unknown")

_CURRENT_ARCH = {
    "x86_64": "x86_64",
    "AMD64": "x86_64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
}.get(_platform.machine(), "unknown")


def current_platform() -> str:
    return _CURRENT_PLATFORM


def current_arch() -> str:
    return _CURRENT_ARCH


def _blank_manifest(runtime_id: str, version: str) -> RuntimeManifest:
    """Placeholder manifest with no download URL — install is not possible yet."""
    return RuntimeManifest(
        schema_version=1,
        runtime_id=runtime_id,
        version=version,
        protocol_version=PROTOCOL_VERSION,
        platform=_CURRENT_PLATFORM,
        arch=_CURRENT_ARCH,
        download_url="",
        sha256="",
        size_bytes=0,
        entrypoint=f"melody-{runtime_id}-worker.exe"
        if sys.platform == "win32"
        else f"melody-{runtime_id}-worker",
        minimum_app_version=None,
        maximum_app_version=None,
    )


def known_manifests() -> dict[str, RuntimeManifest]:
    """Return the static manifest registry keyed by runtime id.

    download_url/sha256 are intentionally empty: installation requires a
    populated, trusted manifest. This registry lets the UI show "not
    installed / install available" without a network round-trip.
    """
    return {
        "vieneu": _blank_manifest("vieneu", "0.1.0"),
        "speech": _blank_manifest("speech", "0.1.0"),
    }


def get_manifest(runtime_id: str) -> RuntimeManifest | None:
    return known_manifests().get(runtime_id)


def is_known_runtime(runtime_id: str) -> bool:
    return runtime_id in KNOWN_RUNTIME_IDS