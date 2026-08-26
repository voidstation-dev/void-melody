"""Execution and concurrency policies for TTS providers and lanes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TypeVar

from app.config import settings

T = TypeVar("T")


class ProviderRoutingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def select_execution_lane(
    lanes: Mapping[str, T], provider_id: str | None
) -> T:
    lane_id = "capcut" if provider_id is None else provider_id
    try:
        return lanes[lane_id]
    except KeyError as exc:
        raise ProviderRoutingError(
            "PROVIDER_LANE_NOT_CONFIGURED",
            f"No execution lane configured for provider '{lane_id}'.",
        ) from exc


@dataclass(frozen=True)
class ProviderExecutionPolicy:
    provider_id: str
    job_concurrency: int
    chunk_concurrency: int
    cache_enabled: bool = True


def get_default_policies() -> dict[str, ProviderExecutionPolicy]:
    return {
        "capcut": ProviderExecutionPolicy(
            provider_id="capcut",
            job_concurrency=settings.capcut_job_concurrency,
            chunk_concurrency=settings.capcut_chunk_concurrency,
            cache_enabled=settings.audio_cache_enabled,
        ),
        "vieneu": ProviderExecutionPolicy(
            provider_id="vieneu",
            job_concurrency=settings.vieneu_job_concurrency,
            chunk_concurrency=settings.vieneu_chunk_concurrency,
            cache_enabled=settings.audio_cache_enabled,
        ),
        "script": ProviderExecutionPolicy(
            provider_id="script",
            job_concurrency=1,
            chunk_concurrency=1,
            cache_enabled=True,
        ),
    }
