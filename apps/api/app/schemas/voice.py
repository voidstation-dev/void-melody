from pydantic import BaseModel


class VoiceResponse(BaseModel):
    id: str
    languageCode: str
    languageShort: str
    voiceType: str
    displayName: str
    resourceId: str | None = None
    capturedAt: str | None = None
    providerId: str | None = None
    gender: str | None = None
    region: str | None = None
    style: str | None = None
    description: str | None = None


class VoiceListResponse(BaseModel):
    items: list[VoiceResponse]
    page: int
    pageSize: int
    total: int
