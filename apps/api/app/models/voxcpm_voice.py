"""VoxCPM2 cloned voice storage.

This model intentionally does NOT reuse tts_custom_voices (VieNeu reference
enrollment). A VoxCPM2 voice is a reference-audio identity asset: the
canonical normalized reference WAV is the profile, and analysis metrics are
stored alongside it for display.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class VoxCpmVoiceModel(Base):
    __tablename__ = "tts_voxcpm_voices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider_id: Mapped[str] = mapped_column(
        String(30), default="voxcpm2", server_default="voxcpm2", nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(
        String(50), default="voxcpm2", server_default="voxcpm2", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="ready", server_default="ready", nullable=False, index=True
    )

    # Canonical normalized reference WAV produced at clone time.
    reference_audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    reference_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reference analysis metrics snapshot (nullable — analysis may fail).
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speech_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    noise_level_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    clipping_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    model_id: Mapped[str] = mapped_column(
        String(100), default="openbmb/VoxCPM2", server_default="openbmb/VoxCPM2", nullable=False
    )
    model_revision: Mapped[str] = mapped_column(
        String(50), default="main", server_default="main", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )