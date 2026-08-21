"""Provider registry for routing TTS jobs to the correct provider.

The registry holds provider *descriptors* (id, label, capabilities), not live
engine instances — model instantiation for VieNeu happens in Phase 4/5 behind a
provider-specific semaphore. This phase only establishes the registry and the
provider_id field on jobs; all existing and new CapCut jobs keep
provider_id='capcut', so CapCut behavior is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from vieneu_core import default_descriptor as vieneu_default_descriptor

# Stable provider ids. These are stored on tts_jobs.provider_id.
CAPCUT = "capcut"
VIENEU = "vieneu"
OMNIVOICE = "omnivoice"


@dataclass(frozen=True)
class Capabilities:
    """Lightweight capabilities for providers.

    Mirrors the capability shape so the registry can answer
    capability queries uniformly without importing external runtimes.
    """

    supports_preset_voices: bool = True
    supports_voice_cloning: bool = False
    supports_streaming: bool = False
    supports_styles: bool = False
    supports_batch: bool = True
    supports_emotion_tags: bool = False
    supports_multilingual: bool = False
    supports_voice_design: bool = False
    supports_target_duration: bool = False
    supports_text_normalization: bool = False
    supports_cross_lingual_clone: bool = False
    max_text_chars: int | None = None
    sample_rate: int | None = None
    languages: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ProviderDescriptor:
    id: str
    label: str
    version: str | None
    capabilities: Capabilities


def _capcut_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor(
        id=CAPCUT,
        label="CapCut",
        version=None,
        capabilities=Capabilities(),
    )


def _vieneu_descriptor() -> ProviderDescriptor:
    desc = vieneu_default_descriptor()
    return ProviderDescriptor(
        id=desc.id,
        label=desc.label,
        version=desc.version,
        capabilities=desc.capabilities,
    )


def _omnivoice_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor(
        id=OMNIVOICE,
        label="OmniVoice",
        version="0.2.1",
        capabilities=Capabilities(
            supports_preset_voices=False,
            supports_voice_cloning=True,
            supports_streaming=False,
            supports_styles=False,
            supports_batch=True,
            supports_emotion_tags=False,
            supports_multilingual=True,
            supports_voice_design=True,
            supports_target_duration=True,
            supports_text_normalization=True,
            supports_cross_lingual_clone=True,
            max_text_chars=5000,
            sample_rate=24000,
        ),
    )


class ProviderRegistry:
    """Registry of known TTS providers, keyed by stable id."""

    def __init__(self) -> None:
        self._descriptors: dict[str, ProviderDescriptor] = {}
        self._default_id = CAPCUT

    def register(self, descriptor: ProviderDescriptor) -> None:
        self._descriptors[descriptor.id] = descriptor

    @property
    def default_provider_id(self) -> str:
        return self._default_id

    def is_known(self, provider_id: str) -> bool:
        return provider_id in self._descriptors

    def get_descriptor(self, provider_id: str) -> ProviderDescriptor | None:
        return self._descriptors.get(provider_id)

    def list_providers(self) -> list[ProviderDescriptor]:
        return list(self._descriptors.values())


provider_registry = ProviderRegistry()
provider_registry.register(_capcut_descriptor())
provider_registry.register(_vieneu_descriptor())
provider_registry.register(_omnivoice_descriptor())
