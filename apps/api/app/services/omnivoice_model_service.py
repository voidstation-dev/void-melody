"""OmniVoice G-OmniVoice model lifecycle service.

Owns model install/verify/load/unload/warmup status for the optional
G-OmniVoice weights. Keeps model lifecycle separate from the OmniVoice
runtime pack lifecycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Pinned revision for reproducible designed voices and migration support.
OMNI_MODEL_ID = "g-omnivoice"
OMNI_MODEL_REVISION = "2025-08-20-a"
OMNI_ENGINE_VERSION = "0.2.1"
OMNI_PROMPT_FORMAT_VERSION = "omnivoice-voice-clone-prompt"


class OmniVoiceModelError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OmniModelStatus:
    model_id: str
    model_revision: str
    engine_version: str
    prompt_format_version: str
    installed: bool
    verified: bool
    loaded: bool
    disk_usage_bytes: int
    path: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelId": self.model_id,
            "modelRevision": self.model_revision,
            "engineVersion": self.engine_version,
            "promptFormatVersion": self.prompt_format_version,
            "installed": self.installed,
            "verified": self.verified,
            "loaded": self.loaded,
            "diskUsageBytes": self.disk_usage_bytes,
            "path": self.path,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
        }


def _model_base_dir() -> Path:
    return Path(settings.vieneu_hf_home) / "omnivoice" / OMNI_MODEL_ID


def _model_revision_dir() -> Path:
    return _model_base_dir() / OMNI_MODEL_REVISION


def _expected_marker_files() -> list[str]:
    """Minimal markers that must exist for a model snapshot to be considered present.

    The real verification is performed by the worker via validate_voice_prompt
    and runtime_info. These markers exist to give the core a cheap local check.
    """
    return ["config.json", "tokenizer", "model.safetensors"]


class OmniVoiceModelService:
    """Core-side coordinator for the G-OmniVoice model snapshot.

    This service does NOT import torch/omnivoice. It manages paths and
    delegates heavy operations to the OmniVoice worker process.
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        self._model_dir = model_dir or _model_revision_dir()

    @property
    def model_id(self) -> str:
        return OMNI_MODEL_ID

    @property
    def model_revision(self) -> str:
        return OMNI_MODEL_REVISION

    @property
    def engine_version(self) -> str:
        return OMNI_ENGINE_VERSION

    @property
    def prompt_format_version(self) -> str:
        return OMNI_PROMPT_FORMAT_VERSION

    @property
    def model_path(self) -> Path:
        return self._model_dir

    def is_installed(self) -> bool:
        if not self._model_dir.is_dir():
            return False
        for name in _expected_marker_files():
            if not (self._model_dir / name).exists():
                return False
        return True

    def resolve_model_path(self) -> Path:
        if not self.is_installed():
            raise OmniVoiceModelError(
                "OMNI_MODEL_NOT_INSTALLED",
                f"G-OmniVoice model {OMNI_MODEL_REVISION} is not installed.",
            )
        return self._model_dir

    def disk_usage_bytes(self) -> int:
        if not self._model_dir.exists():
            return 0
        total = 0
        try:
            for p in self._model_dir.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
        except OSError:
            logger.exception("Failed to compute OmniVoice model disk usage")
        return total

    def status(self) -> OmniModelStatus:
        path = str(self._model_dir) if self._model_dir.exists() else None
        if not self.is_installed():
            return OmniModelStatus(
                model_id=OMNI_MODEL_ID,
                model_revision=OMNI_MODEL_REVISION,
                engine_version=OMNI_ENGINE_VERSION,
                prompt_format_version=OMNI_PROMPT_FORMAT_VERSION,
                installed=False,
                verified=False,
                loaded=False,
                disk_usage_bytes=0,
                path=path,
                error_code="OMNI_MODEL_NOT_INSTALLED",
                error_message="G-OmniVoice model is not installed.",
            )
        return OmniModelStatus(
            model_id=OMNI_MODEL_ID,
            model_revision=OMNI_MODEL_REVISION,
            engine_version=OMNI_ENGINE_VERSION,
            prompt_format_version=OMNI_PROMPT_FORMAT_VERSION,
            installed=True,
            verified=True,  # worker-side verification happens on first load
            loaded=False,   # loaded state is worker-runtime truth
            disk_usage_bytes=self.disk_usage_bytes(),
            path=path,
        )

    def install(self, source_path: Path) -> OmniModelStatus:
        """Accept a trusted model snapshot directory or archive into the managed path.

        For V1 we support copying from a local source directory. Future versions
        can add download/extract/SHA verify here.
        """
        if not source_path.exists():
            raise OmniVoiceModelError(
                "OMNI_MODEL_SOURCE_MISSING",
                f"Model source path does not exist: {source_path}",
            )

        self._model_dir.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            import shutil

            for item in source_path.iterdir():
                dest = self._model_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
        else:
            # Treat as archive and extract in the future.
            raise OmniVoiceModelError(
                "OMNI_MODEL_ARCHIVE_NOT_SUPPORTED",
                "Archive-based model install is not implemented yet.",
            )

        if not self.is_installed():
            raise OmniVoiceModelError(
                "OMNI_MODEL_INSTALL_INCOMPLETE",
                "Model snapshot installed but required marker files are missing.",
            )

        logger.info(
            "OmniVoice model installed: %s@%s at %s",
            OMNI_MODEL_ID,
            OMNI_MODEL_REVISION,
            self._model_dir,
        )
        return self.status()

    def remove(self) -> OmniModelStatus:
        """Remove the pinned model revision directory."""
        if self._model_dir.exists():
            import shutil

            shutil.rmtree(self._model_dir, ignore_errors=True)
            logger.info(
                "OmniVoice model removed: %s@%s",
                OMNI_MODEL_ID,
                OMNI_MODEL_REVISION,
            )
        return self.status()


# Singleton for API reuse.
omnivoice_model_service = OmniVoiceModelService()
