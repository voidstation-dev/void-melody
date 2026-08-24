import { apiFetch } from "@/lib/api-client"
import { TTSJob, BatchJobCreateResponse } from "@/types/tts-job"

export async function fetchTTSJob(jobId: string): Promise<TTSJob> {
  return apiFetch<TTSJob>(`/api/v1/tts/jobs/${jobId}`)
}

export async function createTTSJob(payload: {
  text: string
  voiceType: string
  resourceId?: string
  rate?: number
}): Promise<BatchJobCreateResponse> {
  return apiFetch<BatchJobCreateResponse>("/api/v1/tts/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function createBatchTTSJobs(payload: {
  items: Array<{
    text: string
    voiceType: string
    rate?: number
    sourceFileName?: string
    exportPath?: string
    exportFormat?: "mp3" | "m4a"
  }>
}): Promise<BatchJobCreateResponse> {
  return apiFetch<BatchJobCreateResponse>("/api/v1/tts/jobs/batch", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function deleteTTSJob(jobId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/tts/jobs/${jobId}`, { method: "DELETE" })
}

export async function retryTTSJob(jobId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/tts/jobs/${jobId}/retry`, { method: "POST" })
}
