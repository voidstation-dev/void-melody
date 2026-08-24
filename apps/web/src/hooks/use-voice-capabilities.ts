import { useQuery } from "@tanstack/react-query"
import { voiceQueries } from "@/queries/voices.queries"

export function useVoiceCapabilities() {
  return useQuery(voiceQueries.capabilities())
}
