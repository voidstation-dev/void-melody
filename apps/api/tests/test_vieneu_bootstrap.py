from pathlib import Path
import os

import pytest

from vieneu_core.downloader import VieneuModelArtifacts


@pytest.mark.asyncio
async def test_bootstrap_configures_persistent_runtime_paths(monkeypatch, tmp_path: Path):
    from app.services.vieneu_bootstrap import bootstrap_vieneu_runtime

    artifacts = VieneuModelArtifacts(
        backbone_dir=tmp_path / "backbone",
        onnx_dir=tmp_path / "backbone" / "onnx_int8",
        codec_dir=tmp_path / "codec",
    )

    async def fake_download(hf_home: Path):
        assert hf_home == tmp_path / "models"
        return artifacts

    monkeypatch.setattr(
        "app.services.vieneu_bootstrap.ensure_default_model_artifacts",
        fake_download,
    )

    result = await bootstrap_vieneu_runtime(tmp_path / "models")

    assert result == artifacts
    assert os.environ["VIENEU_HF_HOME"] == str(tmp_path / "models")
    assert os.environ["HF_HOME"] == str(tmp_path / "models")
    assert os.environ["VIENEU_V3_TURBO_MODEL_DIR"] == str(artifacts.backbone_dir)
    assert os.environ["VIENEU_V3_TURBO_ONNX_DIR"] == str(artifacts.onnx_dir)
    assert os.environ["VIENEU_CLONE_ARTIFACT_DIR"] == str(artifacts.backbone_dir)
    assert os.environ["VIENEU_CODEC_ARTIFACT_DIR"] == str(artifacts.codec_dir)
    assert os.environ["VIENEU_V3_TURBO_CODEC_DIR"] == str(artifacts.codec_dir)
