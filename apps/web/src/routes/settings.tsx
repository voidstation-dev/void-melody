import { createFileRoute } from "@tanstack/react-router"
import { UpdateSettings } from "@/components/settings/update-settings"
import { LicenseSettings } from "@/components/settings/license-settings"
import { useTheme } from "next-themes"
import { useTranslation } from "@/hooks/use-translation"
import { Locale } from "@/locales"

export const Route = createFileRoute("/settings")({
  component: SettingsRoute,
})

function SettingsRoute() {
  const { theme, setTheme } = useTheme()
  const { t, locale, setLocale } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <div className="mb-6 shrink-0">
        <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("settings.subtitle")}</p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 pr-2 pb-6">
        <div className="max-w-2xl space-y-4">
          {/* License & Activation Section */}
          <LicenseSettings />

          {/* Language Selection Section */}
          <section aria-labelledby="language-heading" className="rounded-2xl border border-border bg-card p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 id="language-heading" className="font-bold text-base text-foreground">
                  {t("settings.languageHeading")}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("settings.languageDesc")}
                </p>
              </div>
              <select
                aria-label={t("settings.languageLabel")}
                value={locale}
                onChange={(e) => setLocale(e.target.value as Locale)}
                className="min-h-10 rounded-xl border border-border bg-background px-3.5 py-1.5 text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 cursor-pointer"
              >
                <option value="vi">{t("settings.langVi")}</option>
                <option value="en">{t("settings.langEn")}</option>
              </select>
            </div>
          </section>

          {/* Appearance Section */}
          <section aria-labelledby="appearance-heading" className="rounded-2xl border border-border bg-card p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 id="appearance-heading" className="font-bold text-base text-foreground">
                  {t("settings.appearanceHeading")}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("settings.appearanceDesc")}
                </p>
              </div>
              <select
                aria-label={t("settings.themeLabel")}
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="min-h-10 rounded-xl border border-border bg-background px-3.5 py-1.5 text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 cursor-pointer"
              >
                <option value="dark">{t("settings.themeDark")}</option>
                <option value="light">{t("settings.themeLight")}</option>
                <option value="system">{t("settings.themeSystem")}</option>
              </select>
            </div>
          </section>

          {/* App Updates Section */}
          <UpdateSettings />
        </div>
      </div>
    </div>
  )
}
