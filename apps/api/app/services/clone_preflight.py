"""Runtime-backed voice-clone enrollment checks.

The preflight deliberately uses the queue's shared VieNeu provider. Loading a
second model manager here would make the capability check pass while the real
queue later fails, and would also violate the one-model-per-process policy.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class ClonePreflightError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


async def preflight_clone_reference(reference_audio_path: Path) -> None:
    """Enroll a real reference with the exact shared runtime used by TTS."""

    if not reference_audio_path.is_file():
        raise ClonePreflightError(
            "REFERENCE_MISSING",
            "The reference audio is no longer available.",
        )

    # Lazy import avoids a queue/provider import cycle during API startup.
    from app.workers.queue_manager import queue_manager

    provider = queue_manager.provider_registry.get("vieneu")
    preflight = getattr(provider, "preflight_clone_reference", None)
    if not callable(preflight):
        raise ClonePreflightError(
            "CLONE_RUNTIME_UNAVAILABLE",
            "The configured VieNeu runtime cannot enroll reference audio.",
        )

    try:
        await asyncio.wait_for(
            preflight(reference_audio_path),
            timeout=settings.tts_provider_timeout_seconds,
        )
    except ClonePreflightError:
        raise
    except asyncio.TimeoutError as exc:
        logger.warning("Voice clone enrollment preflight timed out")
        raise ClonePreflightError(
            "CLONE_PREFLIGHT_TIMEOUT",
            "Voice enrollment timed out. Check the VieNeu runtime and try again.",
        ) from exc
    except (ImportError, ModuleNotFoundError) as exc:
        logger.warning(
            "Voice clone enrollment runtime dependency unavailable: %s",
            type(exc).__name__,
        )
        raise ClonePreflightError(
            "CLONE_RUNTIME_UNAVAILABLE",
            "The VieNeu runtime cannot enroll references on this installation.",
        ) from exc
    except (FileNotFoundError, OSError) as exc:
        logger.warning(
            "Voice clone enrollment artifact unavailable: %s",
            type(exc).__name__,
        )
        raise ClonePreflightError(
            "CLONE_ARTIFACTS_UNAVAILABLE",
            "Voice-cloning model artifacts are not available in this installation.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Voice clone enrollment preflight failed: %s",
            type(exc).__name__,
        )
        raise ClonePreflightError(
            "CLONE_PREFLIGHT_FAILED",
            "The VieNeu runtime could not enroll this reference audio.",
        ) from exc
