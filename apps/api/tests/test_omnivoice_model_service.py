"""Tests for OmniVoice model lifecycle service."""

from pathlib import Path

import pytest

from app.services.omnivoice_model_service import (
    OMNI_MODEL_ID,
    OMNI_MODEL_REVISION,
    OmniVoiceModelError,
    OmniVoiceModelService,
)


def test_model_status_when_missing(tmp_path: Path):
    svc = OmniVoiceModelService(model_dir=tmp_path / "missing" / "model")
    status = svc.status()
    assert status.model_id == OMNI_MODEL_ID
    assert status.model_revision == OMNI_MODEL_REVISION
    assert status.installed is False
    assert status.verified is False
    assert status.loaded is False
    assert status.error_code == "OMNI_MODEL_NOT_INSTALLED"


def test_model_not_installed_raises_on_resolve(tmp_path: Path):
    svc = OmniVoiceModelService(model_dir=tmp_path / "missing" / "model")
    with pytest.raises(OmniVoiceModelError) as exc_info:
        svc.resolve_model_path()
    assert exc_info.value.code == "OMNI_MODEL_NOT_INSTALLED"


def test_model_install_from_directory(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "config.json").write_text("{}")
    (source / "model.safetensors").write_text("weights")
    tokenizer_dir = source / "tokenizer"
    tokenizer_dir.mkdir()
    (tokenizer_dir / "vocab.json").write_text("[]")

    model_dir = tmp_path / "omnivoice" / "g-omnivoice" / "rev"
    svc = OmniVoiceModelService(model_dir=model_dir)
    result = svc.install(source)

    assert result.installed is True
    assert (model_dir / "config.json").is_file()
    assert (model_dir / "model.safetensors").is_file()
    assert (model_dir / "tokenizer" / "vocab.json").is_file()
    assert svc.resolve_model_path() == model_dir


def test_model_install_missing_source_raises(tmp_path: Path):
    svc = OmniVoiceModelService(model_dir=tmp_path / "model")
    with pytest.raises(OmniVoiceModelError) as exc_info:
        svc.install(tmp_path / "nope")
    assert exc_info.value.code == "OMNI_MODEL_SOURCE_MISSING"


def test_model_remove(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}")
    (model_dir / "model.safetensors").write_text("weights")
    tokenizer_dir = model_dir / "tokenizer"
    tokenizer_dir.mkdir()
    (tokenizer_dir / "vocab.json").write_text("[]")

    svc = OmniVoiceModelService(model_dir=model_dir)
    assert svc.is_installed() is True
    svc.remove()
    assert svc.is_installed() is False


def test_disk_usage_counts_files(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("12345")

    svc = OmniVoiceModelService(model_dir=model_dir)
    assert svc.disk_usage_bytes() == 5
