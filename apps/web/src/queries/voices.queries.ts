import { queryOptions } from "@tanstack/react-query"
import {
  fetchVoices,
  fetchCustomVoices,
  fetchCustomVoice,
  fetchVoiceCapabilities,
} from "@/api/voices"

export const voiceQueries = {
  all: () => ["voices"] as const,
  list: (language?: string, q?: string, providerId?: string, page = 1, pageSize = 500) =>
    queryOptions({
      queryKey: ["voices", language, q, providerId, page, pageSize] as const,
      queryFn: () => fetchVoices(language, q, providerId, page, pageSize),
      staleTime: 5 * 60 * 1000,
      gcTime: 15 * 60 * 1000,
    }),
  capabilities: () =>
    queryOptions({
      queryKey: ["voice-capabilities"] as const,
      queryFn: fetchVoiceCapabilities,
      staleTime: 5 * 60 * 1000,
      gcTime: 15 * 60 * 1000,
      retry: 1,
    }),
  customAll: () => ["custom-voices"] as const,
  customList: (q?: string, page = 1, pageSize = 20) =>
    queryOptions({
      queryKey: ["custom-voices", q, page, pageSize] as const,
      queryFn: () => fetchCustomVoices(q, page, pageSize),
      staleTime: 60 * 1000,
      gcTime: 10 * 60 * 1000,
    }),
  customDetail: (voiceId?: string | null) =>
    queryOptions({
      queryKey: ["custom-voice", voiceId] as const,
      queryFn: () => (voiceId ? fetchCustomVoice(voiceId) : Promise.reject("No voiceId")),
      staleTime: 60 * 1000,
      gcTime: 10 * 60 * 1000,
      enabled: Boolean(voiceId),
    }),
}
