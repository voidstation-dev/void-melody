"""Generic Audio Segment Cache Model for deduplicating repeated synthesis."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioSegmentCacheModel(Base):
    __tablename__ = "audio_segment_cache"

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")
    voice_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    voice_revision: Mapped[str] = mapped_column(String(100), nullable=False, default="v1")
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    style: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="audio/mpeg")
    audio_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, index=True
    )
