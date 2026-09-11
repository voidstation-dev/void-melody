"""Speech runtime coordinator for heavy out-of-process speech runtimes.

Phase 9 policy: only one heavy GPU speech runtime must be active when VRAM is
constrained. This coordinator deliberately does NOT extend
``vieneu_resource_governor`` (plan boundary): VieNeu keeps its own governor;
VoxCPM2 registers here so a VoxCPM2 model load can request an unload of other
registered heavy runtimes first, with explicit user-facing messaging.

No silent provider fallback: if an unload fails, the requester gets an
explicit error and decides what to do.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class SpeechRuntimeCoordinatorError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class _RuntimeEntry:
    owner: str
    unload: callable
    loaded: callable
    label: str


@dataclass
class SpeechRuntimeCoordinator:
    """Registry of heavy speech runtimes + unload-before-load coordination.

    Each runtime registers an async ``unload()`` and a sync ``is_loaded()``
    probe. ``acquire_exclusive`` unloads every *other* loaded runtime before
    the caller loads its own model, so switching engines never co-hosts two
    heavy models in constrained VRAM.
    """

    runtimes: dict[str, _RuntimeEntry] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def register(
        self,
        runtime_id: str,
        *,
        unload: callable,
        is_loaded: callable,
        label: str | None = None,
    ) -> None:
        self.runtimes[runtime_id] = _RuntimeEntry(
            owner=runtime_id,
            unload=unload,
            loaded=is_loaded,
            label=label or runtime_id,
        )

    def unregister(self, runtime_id: str) -> None:
        self.runtimes.pop(runtime_id, None)

    def loaded_runtimes(self) -> list[str]:
        loaded = []
        for runtime_id, entry in self.runtimes.items():
            try:
                if entry.loaded():
                    loaded.append(runtime_id)
            except Exception:  # noqa: BLE001 - probe failures must not crash status
                logger.debug("is_loaded probe failed for %s", runtime_id, exc_info=True)
        return loaded

    async def acquire_exclusive(self, runtime_id: str) -> list[str]:
        """Unload all *other* registered runtimes that currently hold memory.

        Returns the list of runtimes that were unloaded (for explicit UI
        messaging). Raises ``SpeechRuntimeCoordinatorError`` only when an
        unload of another runtime fails — never silently proceeds.
        """
        async with self._lock:
            unloaded: list[str] = []
            for other_id, entry in self.runtimes.items():
                if other_id == runtime_id:
                    continue
                try:
                    if not entry.loaded():
                        continue
                except Exception:
                    continue
                try:
                    await entry.unload()
                    unloaded.append(other_id)
                    logger.info(
                        "SpeechRuntimeCoordinator unloaded '%s' before '%s' load",
                        other_id,
                        runtime_id,
                    )
                except Exception as exc:
                    raise SpeechRuntimeCoordinatorError(
                        "SPEECH_RUNTIME_UNLOAD_FAILED",
                        f"Could not unload '{other_id}' before loading "
                        f"'{runtime_id}': {exc}",
                    ) from exc
            return unloaded


speech_runtime_coordinator = SpeechRuntimeCoordinator()