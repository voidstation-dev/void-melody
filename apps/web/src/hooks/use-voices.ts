import { useQuery } from "@tanstack/react-query"
import { voiceQueries } from "@/queries/voices.queries"

export function useVoices(
  language?: string,
  q?: string,
  providerId?: string,
  page?: number,
  pageSize?: number,
) {
  return useQuery(voiceQueries.list(language, q, providerId, page, pageSize))
}
