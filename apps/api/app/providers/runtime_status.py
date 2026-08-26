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
            from vieneu_core.capabilities import capabilities_for_runtime
            from vieneu_core.engine import probe_runtime

            probe = probe_runtime()
            caps = capabilities_for_runtime(probe)
            is_ready = bool(caps.runtime_available)
            model_installed = all(
                (
                    caps.speaker_encoder_artifact_available,
                    caps.denoiser_artifact_available,
                    caps.codec_encoder_artifact_available,
                )
            )
            return ProviderRuntimeStatus(
                provider_id=VIENEU,
                installed=True,
                available=is_ready,
                model_installed=model_installed,
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
        from app.services.omnivoice_model_service import omnivoice_model_service
        from app.services.runtime_manager import RuntimeManagerService
        from app.services.runtime_manager.models import RuntimeStatus

        runtime_svc = RuntimeManagerService()
        runtime_state = runtime_svc.status(OMNIVOICE)
        model_state = omnivoice_model_service.status()

        installed = runtime_state.status != RuntimeStatus.missing
        available = runtime_state.status == RuntimeStatus.ready
        model_installed = model_state.installed
        model_loaded = model_state.loaded

        if not installed:
            status = "not_installed"
            reason_code = "OMNI_RUNTIME_NOT_INSTALLED"
            reason = "OmniVoice optional runtime is not installed."
        elif runtime_state.status == RuntimeStatus.error:
            status = "broken"
            reason_code = "OMNI_RUNTIME_BROKEN"
            reason = runtime_state.error or "OmniVoice runtime is broken."
        elif not model_installed:
            status = "not_installed"
            reason_code = "OMNI_MODEL_NOT_INSTALLED"
            reason = "OmniVoice runtime is installed but G-OmniVoice model is missing."
        elif not available:
            status = "broken"
            reason_code = "OMNI_RUNTIME_BROKEN"
            reason = "OmniVoice runtime is installed but not ready."
        else:
            status = "ready"
            reason_code = None
            reason = None

        return ProviderRuntimeStatus(
            provider_id=OMNIVOICE,
            installed=installed,
            available=available,
            model_installed=model_installed,
            model_loaded=model_loaded,
            status=status,
            reason_code=reason_code,
            reason=reason,
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
