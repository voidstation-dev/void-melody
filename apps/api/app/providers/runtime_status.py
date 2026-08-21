"""Provider runtime readiness and installation truth."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.providers.registry import CAPCUT, OMNIVOICE, VIENEU


@dataclass(frozen=True)
class ProviderRuntimeStatus:
    """Runtime availability snapshot for a TTS provider.

    Separates static feature support (capabilities) from machine runtime truth.
    """

    provider_id: str
    installed: bool
    available: bool
    model_installed: bool
    model_loaded: bool
    status: str  # "ready" | "not_installed" | "broken" | "downloading"
    reason_code: str | None = None
    reason: str | None = None


def get_provider_runtime_status(provider_id: str) -> ProviderRuntimeStatus:
    """Evaluate and report current runtime truth for a provider."""
    if provider_id == CAPCUT:
        return ProviderRuntimeStatus(
            provider_id=CAPCUT,
            installed=True,
            available=True,
            model_installed=True,
            model_loaded=True,
            status="ready",
        )

    if provider_id == VIENEU:
        try:
            from vieneu_core.engine import probe_runtime

            probe = probe_runtime()
            is_ready = bool(probe.onnxruntime_available or probe.torch_available)
            return ProviderRuntimeStatus(
                provider_id=VIENEU,
                installed=True,
                available=is_ready,
                model_installed=bool(probe.speaker_encoder_artifact_available),
                model_loaded=False,
                status="ready" if is_ready else "broken",
                reason_code=None if is_ready else "VIENEU_RUNTIME_UNAVAILABLE",
                reason=None if is_ready else "VieNeu runtime dependencies are unavailable",
            )
        except Exception as exc:
            return ProviderRuntimeStatus(
                provider_id=VIENEU,
                installed=False,
                available=False,
                model_installed=False,
                model_loaded=False,
                status="broken",
                reason_code="VIENEU_PROBE_FAILED",
                reason=str(exc),
            )

    if provider_id == OMNIVOICE:
        # Check if optional runtime worker & model manifest are installed
        # Prior to O3 installer implementation, default status is not_installed
        current_dir = Path(__file__).resolve().parent
        repo_root = current_dir.parent.parent.parent
        worker_path = repo_root / "apps" / "omnivoice-worker" / "worker.py"
        manifest_path = Path.home() / ".void-melody" / "runtimes" / "omnivoice" / "runtime-manifest.json"

        installed = worker_path.is_file()
        model_installed = manifest_path.is_file()

        if not model_installed:
            return ProviderRuntimeStatus(
                provider_id=OMNIVOICE,
                installed=installed,
                available=False,
                model_installed=False,
                model_loaded=False,
                status="not_installed",
                reason_code="OMNI_RUNTIME_NOT_INSTALLED",
                reason="OmniVoice optional runtime and model are not installed.",
            )

        return ProviderRuntimeStatus(
            provider_id=OMNIVOICE,
            installed=True,
            available=True,
            model_installed=True,
            model_loaded=False,
            status="ready",
        )

    return ProviderRuntimeStatus(
        provider_id=provider_id,
        installed=False,
        available=False,
        model_installed=False,
        model_loaded=False,
        status="not_installed",
        reason_code="UNKNOWN_PROVIDER",
        reason=f"Provider '{provider_id}' is unknown",
    )
