import { ReactNode } from "react"
import { QueryProvider } from "@/components/providers/query-provider"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { I18nProvider } from "@/contexts/i18n-provider"
import { AuthProvider } from "@/contexts/auth-context"
import { TauriProvider } from "@/contexts/tauri-provider"
import { UpdateProvider } from "@/contexts/update-provider"
import { AuthGuard } from "@/components/auth/auth-guard"
import { QueueProvider } from "@/contexts/queue-context"
import { UpdateModal } from "@/components/update/update-modal"

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider attribute="class" defaultTheme="light" forcedTheme="light">
        <I18nProvider>
          <AuthProvider>
            <TauriProvider>
              <UpdateProvider>
                <AuthGuard>
                  <QueueProvider>
                    {children}
                  </QueueProvider>
                </AuthGuard>
                <UpdateModal />
              </UpdateProvider>
            </TauriProvider>
          </AuthProvider>
        </I18nProvider>
      </ThemeProvider>
    </QueryProvider>
  )
}
