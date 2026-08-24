import { useQuery } from "@tanstack/react-query"
import { voiceQueries } from "@/queries/voices.queries"

export function useCustomVoice(voiceId?: string | null) {
  return useQuery(voiceQueries.customDetail(voiceId))
}
