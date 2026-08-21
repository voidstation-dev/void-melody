export type TTSJobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled"

export type TTSJob = {
  id: string
  text: string
  textPreview: string
  voiceType: string
  voiceDisplayName: string
  resourceId: string | null
  rate: number
  providerId?: string | null
  status: TTSJobStatus
  progress: number | null
  batchId: string | null
  batchPosition: number | null
  sourceFileName: string | null
  sourceFileSize: number | null
  audioUrl: string | null
  audioDuration: number | null
  downloadUrl: string | null
  fileSize: number | null
  errorCode: string | null
  errorMessage: string | null
  exportPath: string | null
  exportFormat: string | null
  createdAt: string
  startedAt: string | null
  updatedAt: string
  completedAt: string | null
}

export type BatchJobCreateResponse = {
  batchId: string
  jobs: TTSJob[]
}
