import { useQuery } from "@tanstack/react-query"
import { voiceQueries } from "@/queries/voices.queries"

export function useCustomVoices(q?: string, page = 1, pageSize = 20) {
  return useQuery(voiceQueries.customList(q, page, pageSize))
}
