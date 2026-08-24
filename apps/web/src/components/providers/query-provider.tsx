import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ReactNode } from "react"
import { queryClient as defaultQueryClient } from "@/lib/query-client"

export function QueryProvider({
  children,
  client = defaultQueryClient,
}: {
  children: ReactNode
  client?: QueryClient
}) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
