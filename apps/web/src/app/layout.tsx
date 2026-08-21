import "./globals.css"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { QueryProvider } from "@/components/providers/query-provider"
import { TauriProvider } from "@/contexts/tauri-provider"
import { UpdateProvider } from "@/contexts/update-provider"
import { UpdateModal } from "@/components/update/update-modal"
import { QueueProvider } from "@/contexts/queue-context"
import { I18nProvider } from "@/contexts/i18n-provider"

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
              <TauriProvider>
                <UpdateProvider>
                  <QueueProvider>
                    {children}
                  </QueueProvider>
                  <UpdateModal />
                </UpdateProvider>
              </TauriProvider>
            </I18nProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
