"""Pydantic schemas for the Voice Design (OmniVoice/G-OmniVoice) flow."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceDesignPreviewRequest(BaseModel):
    prompt: str | None = Field(default=None, description="Free-form voice description.")
    language: str | None = Field(default=None, description="Desired language / locale.")
    previewText: str | None = Field(default=None, description="Text used for preview generation.")
    count: int = Field(default=3, ge=1, le=3, description="Number of candidate previews (1-3).")
    attributes: dict[str, str | None] = Field(default_factory=dict)


class VoiceDesignPreviewCandidate(BaseModel):
    id: str
    audioUrl: str


class VoiceDesignPreviewResponse(BaseModel):
    sessionId: str
    compiledInstruction: str
    candidates: list[VoiceDesignPreviewCandidate]


class VoiceDesignCommitRequest(BaseModel):
    candidateId: str
    displayName: str


class VoiceDesignCommitResponse(BaseModel):
    voiceId: str
    displayName: str
    providerId: str
    engineId: str
    voiceKind: str
    status: str


class VoiceDesignSessionResponse(BaseModel):
    sessionId: str
    compiledInstruction: str
    previewText: str
    language: str | None
    status: str
    candidates: list[VoiceDesignPreviewCandidate]


class VoiceDesignCapabilitiesResponse(BaseModel):
    enabled: bool
    providerId: str = "omnivoice"
    engineId: str = "g-omnivoice"
    modelInstalled: bool
    supportsPromptDesign: bool = True
    supportsVoiceClone: bool = False
    reasonCode: str | None = None
    reason: str | None = None
