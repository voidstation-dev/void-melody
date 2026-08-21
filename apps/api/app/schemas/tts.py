from pydantic import BaseModel, Field


class CreateTTSJobRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500000)
    voiceType: str = Field(min_length=1, max_length=150)
    resourceId: str | None = Field(default=None)
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    sourceFileName: str | None = Field(default=None)
    sourceFileSize: int | None = Field(default=None)
    batchId: str | None = Field(default=None)
    batchPosition: int | None = Field(default=None)
    style: str | None = Field(default=None)
    exportPath: str | None = Field(default=None)
    exportFormat: str | None = Field(default=None)


class CreateTTSBatchJobsRequest(BaseModel):
    items: list[CreateTTSJobRequest]


class TTSPreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    voiceType: str = Field(min_length=1, max_length=150)
    resourceId: str | None = Field(default=None)
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    style: str | None = Field(default=None)


class TTSJobResponse(BaseModel):
    id: str
    text: str
    textPreview: str
    voiceType: str
    voiceDisplayName: str
    resourceId: str | None
    rate: float
    providerId: str | None = None
    status: str
    progress: int | None = None
    batchId: str | None = None
    batchPosition: int | None = None
    style: str | None = None
    sourceFileName: str | None = None
    sourceFileSize: int | None = None
    audioUrl: str | None = None
    audioDuration: float | None = None
    downloadUrl: str | None = None
    fileSize: int | None = None
    errorCode: str | None = None
    errorMessage: str | None = None
    exportPath: str | None = None
    exportFormat: str | None = None
    createdAt: str
    startedAt: str | None = None
    updatedAt: str
    completedAt: str | None = None


class BatchJobCreateResponse(BaseModel):
    batchId: str
    jobs: list[TTSJobResponse]


class TTSJobListResponse(BaseModel):
    items: list[TTSJobResponse]
    page: int
    pageSize: int
    total: int


class BatchStatusResponse(BaseModel):
    batchId: str
    totalJobs: int
    completedJobs: int
    failedJobs: int
    pendingJobs: int
    progress: float
    jobs: list[TTSJobResponse]
