import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api-client"
import { VoiceCapabilities } from "@/types/voice"

export function useVoiceCapabilities() {
  return useQuery({
    queryKey: ["voice-capabilities"],
    queryFn: () => apiFetch<VoiceCapabilities>("/api/v1/tts/voices/capabilities"),
    staleTime: 30_000,
    retry: 1,
  })
}
