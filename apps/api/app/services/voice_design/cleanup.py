"""Maintenance cleanup for expired or abandoned Voice Design preview sessions."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.voice_design.preview_store import (
    delete_session,
    load_session,
    preview_base_dir,
)

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_MINUTES = 60


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def cleanup_expired_sessions(
    *,
    max_age_minutes: int = DEFAULT_EXPIRY_MINUTES,
    now: datetime | None = None,
) -> int:
    """Delete preview sessions older than *max_age_minutes*.

    Also removes sessions in terminal states (committed) that were left behind.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=max_age_minutes)
    removed = 0

    base_dir = preview_base_dir()
    if not base_dir.exists():
        return 0

    for session_dir in base_dir.iterdir():
        if not session_dir.is_dir():
            continue
        metadata_path = session_dir / "session.json"
        if not metadata_path.is_file():
            continue

        session = load_session(session_dir.name)
        if session is None:
            if delete_session(session_dir.name):
                removed += 1
            continue

        expires_at = _parse_iso(
            metadata_path.read_text(encoding="utf-8")
            .split('"expires_at"')[1]
            .split(",")[0]
            .split('"')[1]
            if '"expires_at"' in metadata_path.read_text(encoding="utf-8")
            else None
        )
        is_terminal = session.status in ("committed", "expired")
        if is_terminal or (expires_at and expires_at < cutoff):
            if delete_session(session.id):
                removed += 1

    return removed
