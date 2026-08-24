"""Execution and concurrency policies for TTS providers and lanes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config import settings


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
