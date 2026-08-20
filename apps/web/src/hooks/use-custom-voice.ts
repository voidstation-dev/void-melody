import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api-client"
import { CustomVoice } from "@/types/voice"

export function useCustomVoice(voiceId?: string | null) {
  return useQuery({
    queryKey: ["custom-voice", voiceId],
    queryFn: () => apiFetch<CustomVoice>(`/api/v1/tts/voices/custom/${voiceId}`),
    enabled: Boolean(voiceId),
  })
}
