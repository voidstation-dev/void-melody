"""Prepare the pinned VieNeu model cache before the API starts serving work."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from vieneu_core.downloader import (
    VieneuModelArtifacts,
    ensure_default_model_artifacts,
)

logger = logging.getLogger(__name__)


async def bootstrap_vieneu_runtime(hf_home: Path) -> VieneuModelArtifacts:
    """Download missing VieNeu artifacts and configure the shared engine paths."""

    home = Path(hf_home)
    artifacts = await ensure_default_model_artifacts(home)

    # Keep all model downloads in the app's persistent data directory and make
    # the shared provider use the exact pinned snapshot just prepared.
    os.environ["VIENEU_HF_HOME"] = str(home)
    os.environ["HF_HOME"] = str(home)
    os.environ["VIENEU_V3_TURBO_MODEL_DIR"] = str(artifacts.backbone_dir)
    os.environ["VIENEU_V3_TURBO_ONNX_DIR"] = str(artifacts.onnx_dir)
    os.environ["VIENEU_CLONE_ARTIFACT_DIR"] = str(artifacts.backbone_dir)
    os.environ["VIENEU_CODEC_ARTIFACT_DIR"] = str(artifacts.codec_dir)
    os.environ["VIENEU_V3_TURBO_CODEC_DIR"] = str(artifacts.codec_dir)

    logger.info(
        "VieNeu model artifacts ready (backbone=%s, codec=%s)",
        artifacts.backbone_dir,
        artifacts.codec_dir,
    )
    return artifacts
