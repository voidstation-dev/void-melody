"""Abstract backend interface for OmniVoice worker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class OmniBackend(ABC):
    """Worker-side backend contract for model load/unload and inference."""

    @abstractmethod
    def ping(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def runtime_info(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def load_model(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def synthesize(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def create_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def validate_voice_prompt(self, params: dict[str, Any]) -> dict[str, Any]: ...
