"""Tests for the VoxCPM2 provider descriptor (Phase 1)."""

from app.providers.registry import (
    CAPCUT,
    VIENEU,
    VOXCPM2,
    Capabilities,
    provider_registry,
)
from app.providers.runtime_status import get_provider_runtime_status


def test_voxcpm2_descriptor_registered():
    assert provider_registry.is_known(VOXCPM2)
    desc = provider_registry.get_descriptor(VOXCPM2)
    assert desc is not None
    assert desc.id == VOXCPM2
    assert desc.label == "VoxCPM2"


def test_voxcpm2_capabilities_shape():
    desc = provider_registry.get_descriptor(VOXCPM2)
    caps = desc.capabilities
    assert isinstance(caps, Capabilities)
    assert caps.supports_preset_voices is False
    assert caps.supports_voice_cloning is True
    assert caps.supports_streaming is True
    assert caps.supports_styles is True
    assert caps.supports_batch is False
    assert caps.supports_emotion_tags is True
    assert caps.supports_multilingual is True
    assert caps.supports_voice_design is True
    assert caps.supports_cross_lingual_clone is True
    assert caps.sample_rate == 48000


def test_voxcpm2_stable_id():
    assert VOXCPM2 == "voxcpm2"
    assert VOXCPM2 != VIENEU
    assert VOXCPM2 != CAPCUT


def test_list_providers_includes_voxcpm2():
    ids = {p.id for p in provider_registry.list_providers()}
    assert ids == {CAPCUT, VIENEU, VOXCPM2}


def test_voxcpm2_runtime_status_not_installed_before_worker_phase(tmp_path, monkeypatch):
    """Phase 1 has no runtime: status must be honest about not being installed.

    Points the env bootstrap at an empty temp dir so this stays true even on
    machines where the dedicated worker env is actually installed.
    """
    import app.services.voxcpm_env as voxcpm_env

    monkeypatch.setattr(voxcpm_env, "_data_dir", tmp_path)
    status = get_provider_runtime_status(VOXCPM2)
    assert status.provider_id == VOXCPM2
    assert status.installed is False
    assert status.available is False
    assert status.model_installed is False
    assert status.model_loaded is False
    assert status.status == "not_installed"