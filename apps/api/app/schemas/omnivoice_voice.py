"""Pydantic schemas for OmniVoice designed voices."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OmniVoiceVoiceResponse(BaseModel):
    id: str
    display_name: str
    provider_id: str
    engine_id: str
    voice_kind: str
    status: str
    design_prompt: str | None = None
    compiled_instruction: str | None = None
    preview_text: str | None = None
    model_id: str
    model_revision: str
    engine_version: str | None = None
    sample_rate: int | None = None
    voice_revision: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OmniVoiceVoiceListResponse(BaseModel):
    items: list[OmniVoiceVoiceResponse]
    total: int
