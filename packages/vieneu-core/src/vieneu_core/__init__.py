"""vieneu-core: framework-agnostic contracts for the VieNeu-TTS integration.

Public re-exports for the stable surface adapters depend on. This package has
no dependency on FastAPI, SQLAlchemy, Next.js, Tauri, or VoidMelody app state.
"""

from vieneu_core.capabilities import (
    Capabilities,
    ProviderDescriptor,
    RuntimeCapabilities,
    capabilities_for_runtime,
    default_capabilities,
    default_descriptor,
)
from vieneu_core.contracts import (
    AudioFormat,
    Style,
    SynthesizeRequest,
    SynthesizeResult,
    VieneuEngine,
    Voice,
)
from vieneu_core.downloader import (
    MOSS_ONNX_REPO,
    MOSS_ONNX_REVISION,
    VIENEU_V3_TURBO_REPO,
    VIENEU_V3_TURBO_REVISION,
    ModelDownloader,
    ModelFile,
    ModelManifest,
    default_manifests,
    verify_cache,
    verify_file,
)
from vieneu_core.engine import (
    ModelManager,
    RuntimeProbe,
    probe_runtime,
)
from vieneu_core.errors import (
    CloningConsentError,
    InferenceError,
    InvalidStyleError,
    InvalidTextError,
    InvalidVoiceError,
    ModelLoadFailedError,
    ModelNotAvailableError,
    ResourceBusyError,
    VieneuCoreError,
    VoiceNotFoundError,
)
from vieneu_core.voice_profiles import (
    VoiceProfileRequest,
    VoiceProfileResult,
    VoiceProfileValidationError,
    create_reference_profile,
)

__all__ = [
    "MOSS_ONNX_REPO",
    "MOSS_ONNX_REVISION",
    "VIENEU_V3_TURBO_REPO",
    "VIENEU_V3_TURBO_REVISION",
    "AudioFormat",
    "Capabilities",
    "CloningConsentError",
    "InferenceError",
    "InvalidStyleError",
    "InvalidTextError",
    "InvalidVoiceError",
    "ModelDownloader",
    "ModelFile",
    "ModelLoadFailedError",
    "ModelManager",
    "ModelManifest",
    "ModelNotAvailableError",
    "ProviderDescriptor",
    "RuntimeCapabilities",
    "ResourceBusyError",
    "RuntimeProbe",
    "Style",
    "SynthesizeRequest",
    "SynthesizeResult",
    "VieneuCoreError",
    "VieneuEngine",
    "Voice",
    "VoiceNotFoundError",
    "VoiceProfileRequest",
    "VoiceProfileResult",
    "VoiceProfileValidationError",
    "create_reference_profile",
    "default_capabilities",
    "default_descriptor",
    "default_manifests",
    "capabilities_for_runtime",
    "probe_runtime",
    "verify_cache",
    "verify_file",
]
