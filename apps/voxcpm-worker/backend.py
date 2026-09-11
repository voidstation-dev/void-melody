"""Abstract backend interface for the VoxCPM2 worker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VoxCpmBackend(ABC):
    """Worker-side backend contract for model lifecycle and VoxCPM2 inference."""

    @abstractmethod
    def ping(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def runtime_info(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def load_model(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def warmup(self, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def analyze_reference(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def synthesize_clone(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def synthesize_emotional(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def synthesize_ultimate(self, params: dict[str, Any]) -> dict[str, Any]: ...