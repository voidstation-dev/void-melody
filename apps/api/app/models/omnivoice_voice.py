"""OmniVoice designed/cloned/remixed voice storage.

This model intentionally does NOT reuse tts_custom_voices, which is optimized
for VieNeu reference enrollment. OmniVoice voices are identity snapshots
produced from a VoiceClonePrompt, not cloned from user reference audio.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class OmniVoiceVoiceModel(Base):
    __tablename__ = "tts_omnivoice_voices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    provider_id: Mapped[str] = mapped_column(
        String(30), default="omnivoice", server_default="omnivoice", nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(
        String(50), default="g-omnivoice", server_default="g-omnivoice", nullable=False
    )
    voice_kind: Mapped[str] = mapped_column(
        String(20), default="design", server_default="design", nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="ready", server_default="ready", nullable=False, index=True
    )

    design_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    compiled_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    design_attributes_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_preview_audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    prompt_artifact_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    prompt_format_version: Mapped[str] = mapped_column(
        String(50), default="omnivoice-voice-clone-prompt", server_default="omnivoice-voice-clone-prompt", nullable=False
    )

    model_id: Mapped[str] = mapped_column(
        String(50), default="g-omnivoice", server_default="g-omnivoice", nullable=False
    )
    model_revision: Mapped[str] = mapped_column(
        String(50), default="2025-08-20-a", server_default="2025-08-20-a", nullable=False
    )
    engine_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voice_revision: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # License tracking
    license_entitlement_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("license_entitlements.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
