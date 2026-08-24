import { useQuery } from "@tanstack/react-query"
import { historyQueries } from "@/queries/history.queries"

export function useHistory(page = 1) {
  return useQuery(historyQueries.list(page))
}
