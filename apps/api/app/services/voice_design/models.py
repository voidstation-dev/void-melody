"""Internal domain models for Voice Design preview sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now():
    return datetime.now(timezone.utc)


@dataclass
class Candidate:
    id: str
    audio_path: Path
    seed: int | None = None
    attributes_json: str | None = None


@dataclass
class PreviewSession:
    id: str
    compiled_instruction: str
    preview_text: str
    language: str | None
    candidates: list[Candidate] = field(default_factory=list)
    status: str = "active"  # active | committed | expired
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, base_audio_url: str) -> dict[str, Any]:
        return {
            "sessionId": self.id,
            "compiledInstruction": self.compiled_instruction,
            "previewText": self.preview_text,
            "language": self.language,
            "status": self.status,
            "candidates": [
                {
                    "id": c.id,
                    "audioUrl": f"{base_audio_url}/{c.id}/audio",
                    "seed": c.seed,
                }
                for c in self.candidates
            ],
        }
