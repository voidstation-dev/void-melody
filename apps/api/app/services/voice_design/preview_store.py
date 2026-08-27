"""Temporary storage and lifecycle for Voice Design preview sessions."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.voice_design.models import Candidate, PreviewSession

logger = logging.getLogger(__name__)

DEFAULT_PREVIEW_TTL_MINUTES = 60


def preview_base_dir() -> Path:
    return Path(settings.custom_voices_dir).parent / "temp" / "voice-design"


def _session_dir(session_id: str) -> Path:
    return preview_base_dir() / session_id


def _candidate_path(session_id: str, candidate_id: str) -> Path:
    return _session_dir(session_id) / f"candidate-{candidate_id}.wav"


def _session_metadata_path(session_id: str) -> Path:
    return _session_dir(session_id) / "session.json"


def create_session(
    compiled_instruction: str,
    preview_text: str,
    language: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PreviewSession:
    """Create a new empty preview session on disk."""
    session_id = str(uuid.uuid4())
    session_dir = _session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    session = PreviewSession(
        id=session_id,
        compiled_instruction=compiled_instruction,
        preview_text=preview_text,
        language=language,
        metadata=metadata or {},
    )
    _persist(session)
    return session


def _persist(session: PreviewSession) -> None:
    path = _session_metadata_path(session.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": session.id,
        "compiled_instruction": session.compiled_instruction,
        "preview_text": session.preview_text,
        "language": session.language,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "candidates": [
            {
                "id": c.id,
                "audio_path": str(c.audio_path),
                "seed": c.seed,
                "attributes_json": c.attributes_json,
            }
            for c in session.candidates
        ],
        "metadata": session.metadata,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session(session_id: str) -> PreviewSession | None:
    path = _session_metadata_path(session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to load preview session %s", session_id)
        return None

    candidates = [
        Candidate(
            id=c["id"],
            audio_path=Path(c["audio_path"]),
            seed=c.get("seed"),
            attributes_json=c.get("attributes_json"),
        )
        for c in data.get("candidates", [])
    ]
    return PreviewSession(
        id=data["id"],
        compiled_instruction=data["compiled_instruction"],
        preview_text=data["preview_text"],
        language=data.get("language"),
        status=data.get("status", "active"),
        candidates=candidates,
        metadata=data.get("metadata", {}),
    )


def add_candidate(
    session: PreviewSession,
    candidate_id: str,
    audio_path: Path,
    seed: int | None = None,
    attributes_json: str | None = None,
) -> Candidate:
    candidate = Candidate(
        id=candidate_id,
        audio_path=audio_path,
        seed=seed,
        attributes_json=attributes_json,
    )
    session.candidates.append(candidate)
    _persist(session)
    return candidate


def get_candidate_audio_path(session_id: str, candidate_id: str) -> Path | None:
    session = load_session(session_id)
    if session is None:
        return None
    for candidate in session.candidates:
        if candidate.id == candidate_id:
            return candidate.audio_path if candidate.audio_path.is_file() else None
    return None


def mark_committed(session: PreviewSession) -> None:
    session.status = "committed"
    _persist(session)


def delete_session(session_id: str) -> bool:
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        return False
    try:
        import shutil

        shutil.rmtree(session_dir, ignore_errors=True)
        return True
    except OSError:
        logger.exception("Failed to delete preview session %s", session_id)
        return False
