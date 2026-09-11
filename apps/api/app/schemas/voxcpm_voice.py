"""Pydantic schemas for VoxCPM2 cloned voices."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VoxCpmVoiceResponse(BaseModel):
    id: str
    display_name: str
    description: str | None = None
    provider_id: str
    engine_id: str
    status: str
    reference_duration_seconds: float | None = None
    reference_sample_rate: int | None = None
    reference_channels: int | None = None
    reference_transcript: str | None = None
    quality_score: int | None = None
    speech_ratio: float | None = None
    noise_level_db: float | None = None
    clipping_ratio: float | None = None
    model_id: str
    model_revision: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class VoxCpmVoiceListResponse(BaseModel):
    items: list[VoxCpmVoiceResponse]
    total: int


class VoxCpmReferenceAnalysisResponse(BaseModel):
    duration_seconds: float
    source_duration_seconds: float
    selected_start_seconds: float
    selected_end_seconds: float
    reference_duration_seconds: float
    speech_ratio: float
    noise_level_db: float
    clipping_ratio: float
    quality_score: int
    waveform_peaks: list[float]
    warnings: list[str]
    recommended_start_seconds: float | None = None
    recommended_end_seconds: float | None = None
    metrics: dict[str, int] | None = None


# ---- Phase 5: emotional generation ----


class VoxCpmGenerateRequest(BaseModel):
    voice_id: str
    text: str
    emotion: str | None = None
    instruction: str | None = None
    cfg_value: float = 2.0
    inference_timesteps: int = 10
    seed: int | None = None


class VoxCpmGenerateResponse(BaseModel):
    audio_url: str
    output_path: str
    sample_rate: int
    duration_seconds: float
    method: str
    instruction: str | None = None
    voice_id: str
    emotion: str | None = None