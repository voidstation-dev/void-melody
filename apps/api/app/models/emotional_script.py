from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class EmotionalScriptModel(Base):
    __tablename__ = "emotional_scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ScriptRenderModel(Base):
    __tablename__ = "script_renders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id: Mapped[str] = mapped_column(String(36), ForeignKey("emotional_scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    script_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_format: Mapped[str] = mapped_column(String(10), nullable=False, default="mp3")
    output_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    output_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=True)


class ScriptRenderSegmentModel(Base):
    __tablename__ = "script_render_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    render_id: Mapped[str] = mapped_column(String(36), ForeignKey("script_renders.id", ondelete="CASCADE"), nullable=False, index=True)
    script_id: Mapped[str] = mapped_column(String(36), ForeignKey("emotional_scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    line_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resolved_request_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audio_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScriptAudioCacheModel(Base):
    __tablename__ = "script_audio_cache"

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    audio_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
