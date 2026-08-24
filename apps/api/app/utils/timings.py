"""Structured execution timings for profiling and observability."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobTimings:
    job_id: str = ""
    provider: str = ""
    queue_wait_ms: int = 0
    claim_ms: int = 0
    voice_resolution_ms: int = 0
    provider_ms: int = 0
    download_ms: int = 0
    compose_ms: int = 0
    transcode_ms: int = 0
    db_write_ms: int = 0
    total_ms: int = 0
    cache_hit: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    _start_time: float = field(default_factory=time.monotonic)

    def finish(self) -> JobTimings:
        self.total_ms = int((time.monotonic() - self._start_time) * 1000)
        return self

    @contextmanager
    def measure(self, field_name: str):
        start = time.monotonic()
        try:
            yield
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            if hasattr(self, field_name):
                current = getattr(self, field_name)
                setattr(self, field_name, current + elapsed_ms)
            else:
                self.details[field_name] = self.details.get(field_name, 0) + elapsed_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "provider": self.provider,
            "queueWaitMs": self.queue_wait_ms,
            "claimMs": self.claim_ms,
            "voiceResolutionMs": self.voice_resolution_ms,
            "providerMs": self.provider_ms,
            "downloadMs": self.download_ms,
            "composeMs": self.compose_ms,
            "transcodeMs": self.transcode_ms,
            "dbWriteMs": self.db_write_ms,
            "totalMs": self.total_ms,
            "cacheHit": self.cache_hit,
            **({"details": self.details} if self.details else {}),
        }
