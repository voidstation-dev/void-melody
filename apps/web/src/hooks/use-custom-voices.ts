import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api-client"
import { CustomVoice } from "@/types/voice"

type CustomVoiceList = { items: CustomVoice[]; total: number }

export function useCustomVoices(q?: string) {
  return useQuery({
    queryKey: ["custom-voices", q],
    queryFn: () => {
      const params = new URLSearchParams()
      if (q) params.set("q", q)
      return apiFetch<CustomVoiceList>(`/api/v1/tts/voices/custom?${params.toString()}`)
    },
  })
}
