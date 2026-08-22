from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.emotional_script import EmotionalScriptDocument, RenderScope, RenderStatus, SegmentStatus


class ParseScriptRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500_000)
    format: str = "auto"
    title: str | None = None
    original_name: str | None = None


class ScriptCreateRequest(BaseModel):
    document: EmotionalScriptDocument
    title: str | None = None


class ScriptPatchRequest(BaseModel):
    document: EmotionalScriptDocument
    expected_revision: int = Field(ge=1)


class ScriptSummaryResponse(BaseModel):
    id: str
    title: str
    revision: int
    schema_version: int
    document: EmotionalScriptDocument
    created_at: str
    updated_at: str


class ScriptParseResponse(BaseModel):
    document: EmotionalScriptDocument
    line_count: int
    speaker_count: int
    warning_count: int


class RenderCreateRequest(BaseModel):
    scope: RenderScope = "stale"
    output_format: str = "mp3"
    selected_line_ids: list[str] = Field(default_factory=list)


class RenderSegmentResponse(BaseModel):
    id: str
    line_id: str
    ordinal: int
    voice_id: str
    voice_mode: str
    status: SegmentStatus
    progress: int
    request_fingerprint: str
    audio_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class RenderResponse(BaseModel):
    id: str
    script_id: str
    script_revision: int
    status: RenderStatus
    stage: str | None
    progress: int
    total_segments: int
    cached_segments: int
    completed_segments: int
    failed_segments: int
    output_format: str
    output_duration: float | None = None
    output_file_size: int | None = None
    output_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    segments: list[RenderSegmentResponse] = Field(default_factory=list)


class RetryRenderRequest(BaseModel):
    scope: str = "failed"


class ExportRenderRequest(BaseModel):
    output_format: str = "mp3"
    directory: str | None = None


class PreviewResponse(BaseModel):
    line_id: str
    emitted_text: str
    native_cues: list[str]
    approximated_intents: list[str]
    unsupported_intents: list[str]
    warnings: list[str]
