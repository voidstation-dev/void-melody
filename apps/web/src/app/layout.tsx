import "./globals.css"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { QueryProvider } from "@/components/providers/query-provider"
import { TauriProvider } from "@/contexts/tauri-provider"
import { UpdateProvider } from "@/contexts/update-provider"
import { UpdateModal } from "@/components/update/update-modal"
import { QueueProvider } from "@/contexts/queue-context"
import { I18nProvider } from "@/contexts/i18n-provider"
import { AuthProvider } from "@/contexts/auth-context"
import { AuthGuard } from "@/components/auth/auth-guard"

export const metadata = {
  title: "Melody - Text to Speech Studio",
  description: "A premium Text to Speech Studio created by VoidStation.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
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
      </body>
    </html>
  )
}
