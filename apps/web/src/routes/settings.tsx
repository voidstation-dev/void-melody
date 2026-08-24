import { createFileRoute } from "@tanstack/react-router"
import { UpdateSettings } from "@/components/settings/update-settings"
import { LicenseSettings } from "@/components/settings/license-settings"
import { useTheme } from "next-themes"
import { useTranslation } from "@/hooks/use-translation"
import { Locale } from "@/locales"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Globe, Palette, Moon, Sun, Laptop } from "lucide-react"

export const Route = createFileRoute("/settings")({
  component: SettingsRoute,
})

function SettingsRoute() {
  const { theme, setTheme } = useTheme()
  const { t, locale, setLocale } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <div className="mb-6 shrink-0">
        <h1 className="text-2xl font-bold tracking-tight">{t("settings.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("settings.subtitle")}</p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 pr-2 pb-6">
        <div className="max-w-2xl space-y-4">
          {/* License & Activation Section */}
          <LicenseSettings />

          {/* Language Selection Section */}
          <section
            aria-labelledby="language-heading"
            className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs hover:border-border transition-colors"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Globe className="h-4.5 w-4.5" />
                </div>
                <div>
                  <h2 id="language-heading" className="font-bold text-sm sm:text-base text-foreground">
                    {t("settings.languageHeading")}
                  </h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {t("settings.languageDesc")}
                  </p>
                </div>
              </div>

              <div className="w-full sm:w-[210px] shrink-0">
                <Select
                  value={locale}
                  onValueChange={(val) => setLocale(val as Locale)}
                >
                  <SelectTrigger aria-label={t("settings.languageLabel")}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent align="end">
                    <SelectItem value="vi">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">🇻🇳</span>
                        <span>{t("settings.langVi")}</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="en">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">🇺🇸</span>
                        <span>{t("settings.langEn")}</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          {/* Appearance Section */}
          <section
            aria-labelledby="appearance-heading"
            className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs hover:border-border transition-colors"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Palette className="h-4.5 w-4.5" />
                </div>
                <div>
                  <h2 id="appearance-heading" className="font-bold text-sm sm:text-base text-foreground">
                    {t("settings.appearanceHeading")}
                  </h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {t("settings.appearanceDesc")}
                  </p>
                </div>
              </div>

              <div className="w-full sm:w-[210px] shrink-0">
                <Select
                  value={theme ?? "system"}
                  onValueChange={setTheme}
                >
                  <SelectTrigger aria-label={t("settings.themeLabel")}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent align="end">
                    <SelectItem value="dark">
                      <div className="flex items-center gap-2">
                        <Moon className="h-3.5 w-3.5 text-primary" />
                        <span>{t("settings.themeDark")}</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="light">
                      <div className="flex items-center gap-2">
                        <Sun className="h-3.5 w-3.5 text-amber-500" />
                        <span>{t("settings.themeLight")}</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="system">
                      <div className="flex items-center gap-2">
                        <Laptop className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>{t("settings.themeSystem")}</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          {/* App Updates Section */}
          <UpdateSettings />
        </div>
      </div>
    </div>
  )
}
