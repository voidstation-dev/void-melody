from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomVoiceResponse(BaseModel):
    id: str
    display_name: str
    transcript: str
    consent_given: bool
    created_at: datetime
    provider_id: str = "vieneu"
    engine_id: str = "v3turbo"
    status: str = "ready"
    duration_seconds: float | None = None
    source_duration_seconds: float | None = None
    reference_duration_seconds: float | None = None
    selected_start_seconds: float | None = None
    selected_end_seconds: float | None = None
    quality_score: int | None = None
    consent_version: str = "voice-lab-v1"
    profile_format_version: str = "reference-v1"
    engine_version: str | None = None
    denoise_mode: str = "auto"
    denoise_applied: bool | None = None
    clone_mode: str = "fidelity"
    speaker_similarity_score: float | None = None
    calibration_quality_score: int | None = None
    calibration_available: bool = False
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomVoiceListResponse(BaseModel):
    items: list[CustomVoiceResponse]
    total: int


class VoiceCapabilitiesResponse(BaseModel):
    provider_id: str
    engine_id: str
    engine_version: str | None
    runtime_available: bool
    device: str
    backend: str
    supports_preset_voices: bool
    supports_voice_cloning: bool
    supports_denoise: bool
    supports_streaming: bool
    torch_available: bool = False
    torchaudio_available: bool = False
    clone_frontend_available: bool = False
    speaker_encoder_artifact_available: bool = False
    denoiser_artifact_available: bool = False
    codec_encoder_artifact_available: bool = False
    reason_code: str | None
    reason: str | None


class VoiceAnalysisResponse(BaseModel):
    duration_seconds: float
    source_duration_seconds: float | None = None
    reference_duration_seconds: float | None = None
    selected_start_seconds: float
    selected_end_seconds: float
    speech_ratio: float
    noise_level_db: float
    clipping_ratio: float
    quality_score: int
    waveform_peaks: list[float]
    warnings: list[str]
    estimated_snr_db: float | None = None
    noise_floor_dbfs: float | None = None
    silence_ratio: float | None = None
    level_stability: float | None = None
    recommended_start_seconds: float | None = None
    recommended_end_seconds: float | None = None
    metrics: dict[str, int] | None = None
