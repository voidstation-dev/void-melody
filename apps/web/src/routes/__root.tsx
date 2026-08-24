import { createRootRouteWithContext, Outlet } from "@tanstack/react-router"
import type { QueryClient } from "@tanstack/react-query"
import { AppProviders } from "@/app/app-providers"
import { AppShell } from "@/app/app-shell"

export interface RouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
})

function RootComponent() {
  return (
    <AppProviders>
      <AppShell>
        <Outlet />
      </AppShell>
    </AppProviders>
  )
}
