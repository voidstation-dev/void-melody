import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CustomVoiceModel(Base):
    __tablename__ = "tts_custom_voices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[str] = mapped_column(
        String(30), default="voice-lab-v1", server_default="voice-lab-v1", nullable=False
    )
    provider_id: Mapped[str] = mapped_column(
        String(30), default="vieneu", server_default="vieneu", nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(
        String(50), default="v3turbo", server_default="v3turbo", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="ready", server_default="ready", nullable=False, index=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected_start_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected_end_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_warnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
