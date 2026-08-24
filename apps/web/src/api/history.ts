import { apiFetch } from "@/lib/api-client"
import { TTSJob } from "@/types/tts-job"

export type HistoryResponse = {
  items: TTSJob[]
  page: number
  pageSize: number
  total: number
}

export async function fetchHistory(page = 1): Promise<HistoryResponse> {
  return apiFetch<HistoryResponse>(`/api/v1/tts/jobs?page=${page}`)
}
