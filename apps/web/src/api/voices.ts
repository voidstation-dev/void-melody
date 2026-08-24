import { apiFetch } from "@/lib/api-client"
import { VoiceListResponse, CustomVoice, VoiceCapabilities } from "@/types/voice"

export type CustomVoiceListResponse = { items: CustomVoice[]; total: number }

export async function fetchVoices(
  language?: string,
  q?: string,
  providerId?: string,
  page = 1,
  pageSize = 500,
): Promise<VoiceListResponse> {
  const params = new URLSearchParams()
  if (language) params.set("language", language)
  if (q) params.set("q", q)
  if (providerId) params.set("provider_id", providerId)
  params.set("page", String(page))
  params.set("page_size", String(pageSize))
  const qs = params.toString()
  return apiFetch<VoiceListResponse>(`/api/v1/voices${qs ? `?${qs}` : ""}`)
}

export async function fetchCustomVoices(q?: string, page = 1, pageSize = 20): Promise<CustomVoiceListResponse> {
  const params = new URLSearchParams()
  if (q) params.set("q", q)
  params.set("page", String(page))
  params.set("page_size", String(pageSize))
  return apiFetch<CustomVoiceListResponse>(`/api/v1/tts/voices/custom?${params.toString()}`)
}

export async function fetchCustomVoice(voiceId: string): Promise<CustomVoice> {
  return apiFetch<CustomVoice>(`/api/v1/tts/voices/custom/${voiceId}`)
}

export async function deleteCustomVoice(voiceId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/tts/voices/custom/${voiceId}`, { method: "DELETE" })
}

export async function fetchVoiceCapabilities(): Promise<VoiceCapabilities> {
  return apiFetch<VoiceCapabilities>("/api/v1/tts/voices/capabilities")
}
