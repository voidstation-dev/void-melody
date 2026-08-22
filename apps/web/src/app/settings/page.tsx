"use client"
import { PageContainer } from "@/components/app-shell/page-container"
import { UpdateSettings } from "@/components/settings/update-settings"
import { LicenseSettings } from "@/components/settings/license-settings"
import { useTheme } from "next-themes"
import { useTranslation } from "@/hooks/use-translation"
import { Locale } from "@/locales"
import { useTrialStatus } from "@/contexts/trial-context"

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { t, locale, setLocale } = useTranslation()
  const trial = useTrialStatus()
  const expiresLabel = trial.status.expires_at
    ? new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(trial.status.expires_at * 1000))
    : "—"
  const remainingLabel = trial.status.remaining_seconds > 86400
    ? `${Math.ceil(trial.status.remaining_seconds / 86400)} ngày`
    : trial.status.remaining_seconds > 0
      ? `${Math.ceil(trial.status.remaining_seconds / 3600)} giờ`
      : "đã hết hạn"

  return (
    <PageContainer>
      <div className="overflow-y-auto pb-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("settings.subtitle")}</p>
        </div>

        <div className="max-w-2xl space-y-4">
          {/* License & Activation Section */}
          <LicenseSettings />

          <section aria-labelledby="trial-heading" className={`rounded-2xl border p-6 shadow-sm ${trial.status.can_synthesize ? "border-border bg-card" : "border-red-200 bg-red-50/60"}`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="trial-heading" className="font-bold text-base text-foreground">Thời gian dùng thử</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {trial.status.override ? "Chế độ phát triển — trial gate đang tắt." : trial.status.can_synthesize ? `Còn ${remainingLabel} sử dụng.` : "Đã hết thời gian tạo audio mới. Audio cũ vẫn có thể phát và tải xuống."}
                </p>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${trial.status.can_synthesize ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                {trial.status.status}
              </span>
            </div>
            <p className="mt-4 text-xs font-semibold text-muted-foreground">Hết hạn: <span className="text-foreground">{expiresLabel}</span></p>
          </section>

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
    </PageContainer>
  )
}
