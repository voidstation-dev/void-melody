import { ReactNode } from "react"
import { AppHeader } from "@/components/app-shell/app-header"
import { AppSidebar } from "@/components/app-shell/app-sidebar"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-screen max-h-screen max-w-screen flex-col bg-background text-foreground font-sans overflow-hidden">
      <div className="shrink-0">
        <AppHeader />
      </div>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <AppSidebar />
        <main className="min-h-0 min-w-0 flex-1 bg-muted/30 p-4 sm:p-6 overflow-y-auto overflow-x-hidden flex flex-col">{children}</main>
      </div>
    </div>
  )
}
