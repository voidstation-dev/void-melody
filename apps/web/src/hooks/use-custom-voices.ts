import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api-client"
import { CustomVoice } from "@/types/voice"

type CustomVoiceList = { items: CustomVoice[]; total: number }

export function useCustomVoices(q?: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["custom-voices", q, page, pageSize],
    queryFn: () => {
      const params = new URLSearchParams()
      if (q) params.set("q", q)
      params.set("page", String(page))
      params.set("page_size", String(pageSize))
      return apiFetch<CustomVoiceList>(`/api/v1/tts/voices/custom?${params.toString()}`)
    },
  })
}
