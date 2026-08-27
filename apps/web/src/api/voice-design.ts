import { apiFetch } from "@/lib/api-client"
import type {
  VoiceDesignCommitRequest,
  VoiceDesignCommitResponse,
  VoiceDesignPreviewRequest,
  VoiceDesignPreviewResponse,
} from "@/types/voice-design"

export async function createVoiceDesignPreviews(
  request: VoiceDesignPreviewRequest,
): Promise<VoiceDesignPreviewResponse> {
  return apiFetch<VoiceDesignPreviewResponse>("/api/v1/tts/voice-design/previews", {
    method: "POST",
    body: JSON.stringify(request),
  })
}

export function resolveCandidateAudioUrl(audioUrl: string): string {
  return audioUrl.startsWith("/") ? `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}${audioUrl}` : audioUrl
}

export async function commitVoiceDesign(
  sessionId: string,
  request: VoiceDesignCommitRequest,
): Promise<VoiceDesignCommitResponse> {
  return apiFetch<VoiceDesignCommitResponse>(
    `/api/v1/tts/voice-design/sessions/${sessionId}/commit`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  )
}
