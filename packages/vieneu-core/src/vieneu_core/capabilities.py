"""Capability flags and provider descriptor for VieNeu.

Capabilities describe what a VieNeu engine instance supports (preset voices,
cloning, streaming, styles, batch, emotion tags) plus operational limits
(sample rate, max text length). The adapter (Phase 3+) uses these to route
requests and to answer capability queries from the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine import RuntimeProbe


@dataclass(frozen=True)
class Capabilities:
    supports_preset_voices: bool = True
    supports_voice_cloning: bool = True
    supports_streaming: bool = True
    supports_styles: bool = True
    supports_batch: bool = True
    supports_emotion_tags: bool = True
    max_text_chars: int | None = 256
    sample_rate: int = 48000


@dataclass(frozen=True)
class ProviderDescriptor:
    """Describes the VieNeu provider to the rest of VoidMelody."""

    id: str
    label: str
    version: str | None
    capabilities: Capabilities


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Capabilities available on the current installed runtime."""

    provider_id: str = "vieneu"
    engine_id: str = "v3turbo"
    engine_version: str | None = None
    device: str = "cpu"
    backend: str = "onnx"
    runtime_available: bool = False
    supports_preset_voices: bool = False
    supports_voice_cloning: bool = False
    supports_denoise: bool = False
    supports_streaming: bool = False
    torch_available: bool = False
    torchaudio_available: bool = False
    clone_frontend_available: bool = False
    speaker_encoder_artifact_available: bool = False
    denoiser_artifact_available: bool = False
    codec_encoder_artifact_available: bool = False
    # Reference-text capability policy (engine-aware, V4-ready).
    # ignored  → engine does not consume reference text; UI may hide the field.
    # optional → profile may store reference text; enrollment can proceed without it.
    # required → enrollment cannot proceed without valid reference text.
    reference_text_policy: str = "optional"
    reference_text_used_for_enrollment: bool = False
    reference_min_seconds: float = 3.0
    reference_max_seconds: float = 8.0
    reason_code: str | None = None
    reason: str | None = None


def capabilities_for_runtime(
    probe: RuntimeProbe, *, engine_version: str | None = None
) -> RuntimeCapabilities:
    """Translate a lightweight runtime probe into an honest feature gate."""

    runtime_available = (
        probe.onnxruntime_available
        if probe.backend == "onnx"
        else probe.torch_cuda_available
    )
    if not runtime_available:
        return RuntimeCapabilities(
            engine_version=engine_version,
            device=probe.device,
            backend=probe.backend,
            torch_available=probe.torch_available,
            torchaudio_available=probe.torchaudio_available,
            clone_frontend_available=probe.torch_available and probe.torchaudio_available,
            speaker_encoder_artifact_available=probe.speaker_encoder_artifact_available,
            denoiser_artifact_available=probe.denoiser_artifact_available,
            codec_encoder_artifact_available=probe.codec_encoder_artifact_available,
            reason_code="RUNTIME_UNAVAILABLE",
            reason="VieNeu runtime is not installed for this device.",
        )

    clone_frontend_available = probe.torch_available and probe.torchaudio_available
    clone_artifacts_available = (
        probe.speaker_encoder_artifact_available
        and probe.denoiser_artifact_available
        and probe.codec_encoder_artifact_available
    )
    supports_voice_cloning = clone_frontend_available and clone_artifacts_available
    reason_code: str | None = None
    reason: str | None = None
    if not clone_frontend_available:
        reason_code = "CLONE_FRONTEND_UNAVAILABLE"
        reason = "Voice cloning requires the torch and torchaudio speaker frontend."
    elif not clone_artifacts_available:
        reason_code = "CLONE_ARTIFACTS_UNAVAILABLE"
        reason = "Voice cloning model artifacts are not available in this installation."

    return RuntimeCapabilities(
        engine_version=engine_version,
        device=probe.device,
        backend=probe.backend,
        runtime_available=True,
        supports_preset_voices=True,
        supports_voice_cloning=supports_voice_cloning,
        supports_denoise=probe.denoiser_artifact_available,
        supports_streaming=probe.backend == "onnx",
        torch_available=probe.torch_available,
        torchaudio_available=probe.torchaudio_available,
        clone_frontend_available=clone_frontend_available,
        speaker_encoder_artifact_available=probe.speaker_encoder_artifact_available,
        denoiser_artifact_available=probe.denoiser_artifact_available,
        codec_encoder_artifact_available=probe.codec_encoder_artifact_available,
        reason_code=reason_code,
        reason=reason,
    )


def default_capabilities() -> Capabilities:
    """Return the VieNeu v3 Turbo capability set (surveyed in Phase 0).

    The default ``max_text_chars`` reflects the per-chunk character budget the
    engine uses internally (``max_chars=256`` in ``V3TurboVieNeuTTS.infer``);
    the adapter chunks longer inputs before calling the engine (Phase 5).
    """

    return Capabilities(
        supports_preset_voices=True,
        supports_voice_cloning=True,
        supports_streaming=True,
        supports_styles=True,
        supports_batch=True,
        supports_emotion_tags=True,
        max_text_chars=256,
        sample_rate=48000,
    )


def default_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor(
        id="vieneu",
        label="VieNeu",
        version=None,
        capabilities=default_capabilities(),
    )
