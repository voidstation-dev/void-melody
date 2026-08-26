"""Tests for ProviderRegistry and ProviderRuntimeStatus."""

from app.providers.registry import (
    CAPCUT,
    OMNIVOICE,
    VIENEU,
    Capabilities,
    ProviderRegistry,
    provider_registry,
)
from app.providers.runtime_status import (
    ProviderRuntimeStatus,
    get_provider_runtime_status,
)


def test_default_provider_is_capcut():
    assert provider_registry.default_provider_id == CAPCUT


def test_known_providers_registered():
    assert provider_registry.is_known(CAPCUT)
    assert provider_registry.is_known(VIENEU)
    assert provider_registry.is_known(OMNIVOICE)
    assert not provider_registry.is_known("bogus")


def test_registry_uses_common_capability_type_for_all():
    for desc in provider_registry.list_providers():
        assert isinstance(desc.capabilities, Capabilities), f"{desc.id} capabilities is not app Capabilities instance"


def test_capcut_descriptor_shape():
    desc = provider_registry.get_descriptor(CAPCUT)
    assert desc is not None
    assert desc.id == CAPCUT
    assert desc.label == "CapCut"
    # CapCut legacy: no cloning, no streaming, no styles.
    assert desc.capabilities.supports_preset_voices is True
    assert desc.capabilities.supports_voice_cloning is False
    assert desc.capabilities.supports_multilingual is False
    assert desc.capabilities.supports_voice_design is False
    assert desc.capabilities.supports_target_duration is False


def test_vieneu_descriptor_from_core_normalized():
    desc = provider_registry.get_descriptor(VIENEU)
    assert desc is not None
    assert desc.id == VIENEU
    assert desc.label == "VieNeu"
    # VieNeu normalized capabilities
    assert desc.capabilities.supports_voice_cloning is True
    assert desc.capabilities.supports_streaming is True
    assert desc.capabilities.sample_rate == 48000
    # Normalized common fields
    assert desc.capabilities.supports_multilingual is False
    assert desc.capabilities.supports_voice_design is False
    assert desc.capabilities.supports_target_duration is False
    assert desc.capabilities.supports_text_normalization is False
    assert desc.capabilities.supports_cross_lingual_clone is False
    assert desc.capabilities.languages == ("vi-VN", "en-US")


def test_omnivoice_descriptor_shape():
    desc = provider_registry.get_descriptor(OMNIVOICE)
    assert desc is not None
    assert desc.id == OMNIVOICE
    assert desc.label == "OmniVoice"
    assert desc.version == "0.2.1"
    assert desc.capabilities.supports_multilingual is True
    assert desc.capabilities.supports_voice_design is True
    assert desc.capabilities.supports_target_duration is True
    assert desc.capabilities.supports_voice_cloning is True
    assert desc.capabilities.sample_rate == 24000


def test_list_providers_returns_all():
    providers = provider_registry.list_providers()
    ids = {p.id for p in providers}
    assert ids == {CAPCUT, VIENEU, OMNIVOICE}


def test_empty_registry_is_safe():
    reg = ProviderRegistry()
    assert reg.default_provider_id == CAPCUT
    assert reg.get_descriptor(CAPCUT) is None
    assert reg.list_providers() == []


def test_omnivoice_runtime_status_not_installed():
    status = get_provider_runtime_status(OMNIVOICE)
    assert isinstance(status, ProviderRuntimeStatus)
    assert status.provider_id == OMNIVOICE
    # Source worker file in repo and unverified manifest must not mean installed/available
    assert status.installed is False
    assert status.available is False
    assert status.model_installed is False
    assert status.status == "not_installed"
    assert status.reason_code in ("OMNI_RUNTIME_NOT_INSTALLED", "OMNI_MODEL_NOT_INSTALLED")


def test_vieneu_runtime_status_reuses_core_runtime_truth():
    status = get_provider_runtime_status(VIENEU)
    assert isinstance(status, ProviderRuntimeStatus)
    assert status.provider_id == VIENEU
    assert status.status in ("ready", "broken")


def test_capcut_runtime_status_ready():
    status = get_provider_runtime_status(CAPCUT)
    assert isinstance(status, ProviderRuntimeStatus)
    assert status.provider_id == CAPCUT
    assert status.installed is True
    assert status.available is True
    assert status.status == "ready"


def test_unknown_provider_runtime_status():
    status = get_provider_runtime_status("unknown_id")
    assert status.installed is False
    assert status.available is False
    assert status.status == "not_installed"
    assert status.reason_code == "UNKNOWN_PROVIDER"
