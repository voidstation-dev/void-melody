import { queryOptions } from "@tanstack/react-query"
import { fetchHistory } from "@/api/history"

export const historyQueries = {
  all: () => ["history"] as const,
  list: (page = 1) =>
    queryOptions({
      queryKey: ["history", page] as const,
      queryFn: () => fetchHistory(page),
      staleTime: 30 * 1000,
      gcTime: 5 * 60 * 1000,
    }),
}
