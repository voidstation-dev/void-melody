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
import { TrialProvider } from "@/contexts/trial-context"
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata = {
  title: "Melody - Text to Speech Studio",
  description: "A premium Text to Speech Studio created by VoidStation.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning className={cn("font-sans", geist.variable)}>
      <body>
        <QueryProvider>
          <ThemeProvider attribute="class" defaultTheme="light" forcedTheme="light">
            <I18nProvider>
              <AuthProvider>
                <TauriProvider>
                  <TrialProvider>
                    <UpdateProvider>
                      <AuthGuard>
                        <QueueProvider>
                          {children}
                        </QueueProvider>
                      </AuthGuard>
                      <UpdateModal />
                    </UpdateProvider>
                  </TrialProvider>
                </TauriProvider>
              </AuthProvider>
            </I18nProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
