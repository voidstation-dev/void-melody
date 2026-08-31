import { createFileRoute } from "@tanstack/react-router"
import { UpdateSettings } from "@/components/settings/update-settings"
import { LicenseSettings } from "@/components/settings/license-settings"
import { LocalAiSettings } from "@/components/settings/local-ai-settings"
import { ThemePalettePicker } from "@/components/settings/theme-palette-picker"
import { RadiusCustomizer } from "@/components/settings/radius-customizer"
import { useTheme } from "next-themes"
import { useTranslation } from "@/hooks/use-translation"
import { Locale } from "@/locales"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Globe, Palette, Moon, Sun, Laptop, ShieldCheck, Cpu, Sliders, Check } from "lucide-react"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/settings")({
  component: SettingsRoute,
})

function SettingsRoute() {
  const { theme, setTheme } = useTheme()
  const { t, locale, setLocale } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="mb-5 shrink-0">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">{t("settings.title")}</h1>
        <p className="mt-1 text-xs sm:text-sm text-muted-foreground">{t("settings.subtitle")}</p>
      </div>

      {/* Tabbed Navigation & Content */}
      <Tabs defaultValue="general" className="flex-1 flex flex-col min-h-0">
        <div className="shrink-0 mb-4">
          <TabsList className="grid w-full grid-cols-3 max-w-xl h-11 p-1 bg-muted/70 rounded-xl border border-border/40 shadow-2xs">
            <TabsTrigger
              value="general"
              className="flex items-center justify-center gap-2 text-xs sm:text-sm font-semibold rounded-lg transition-all"
            >
              <Sliders className="h-4 w-4" />
              <span>{t("settings.tabGeneral")}</span>
            </TabsTrigger>
            <TabsTrigger
              value="license"
              className="flex items-center justify-center gap-2 text-xs sm:text-sm font-semibold rounded-lg transition-all"
            >
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>{t("settings.tabLicense")}</span>
            </TabsTrigger>
            <TabsTrigger
              value="local-ai"
              className="flex items-center justify-center gap-2 text-xs sm:text-sm font-semibold rounded-lg transition-all"
            >
              <Cpu className="h-4 w-4 text-primary" />
              <span>{t("settings.tabLocalAi")}</span>
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 pr-1 sm:pr-2 pb-8">
          <div className="max-w-3xl space-y-4">
            {/* TAB 1: GENERAL SETTINGS */}
            <TabsContent value="general" className="mt-0 space-y-4">
              {/* Appearance & Themes Section */}
              <section
                aria-labelledby="appearance-heading"
                className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs hover:border-border transition-colors space-y-5"
              >
                <div className="flex flex-col gap-4">
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

                  {/* 3-Button Mode Segmented Selector */}
                  <div className="grid grid-cols-3 gap-2 sm:gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => setTheme("light")}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-xl border p-3 text-xs sm:text-sm font-semibold transition-all cursor-pointer",
                        theme === "light"
                          ? "border-primary bg-primary/10 text-primary shadow-xs font-bold ring-1 ring-primary/30"
                          : "border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                    >
                      <Sun className="h-4 w-4 text-amber-500 shrink-0" />
                      <span>{t("settings.themeLight")}</span>
                      {theme === "light" && <Check className="h-3.5 w-3.5 ml-auto text-primary" />}
                    </button>

                    <button
                      type="button"
                      onClick={() => setTheme("dark")}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-xl border p-3 text-xs sm:text-sm font-semibold transition-all cursor-pointer",
                        theme === "dark"
                          ? "border-primary bg-primary/10 text-primary shadow-xs font-bold ring-1 ring-primary/30"
                          : "border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                    >
                      <Moon className="h-4 w-4 text-primary shrink-0" />
                      <span>{t("settings.themeDark")}</span>
                      {theme === "dark" && <Check className="h-3.5 w-3.5 ml-auto text-primary" />}
                    </button>

                    <button
                      type="button"
                      onClick={() => setTheme("system")}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-xl border p-3 text-xs sm:text-sm font-semibold transition-all cursor-pointer",
                        theme === "system"
                          ? "border-primary bg-primary/10 text-primary shadow-xs font-bold ring-1 ring-primary/30"
                          : "border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                    >
                      <Laptop className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span>{t("settings.themeSystem")}</span>
                      {theme === "system" && <Check className="h-3.5 w-3.5 ml-auto text-primary" />}
                    </button>
                  </div>
                </div>

                {/* TweakCN Theme Palette Picker */}
                <div className="pt-2 border-t border-border/50">
                  <ThemePalettePicker />
                </div>

                {/* Radius Customizer */}
                <RadiusCustomizer />
              </section>

              {/* Language Section */}
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

                  {/* 2-Button Language Segmented Selector */}
                  <div className="grid grid-cols-2 gap-2 w-full sm:w-[280px] shrink-0">
                    <button
                      type="button"
                      onClick={() => setLocale("vi" as Locale)}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-xl border py-2.5 px-3 text-xs font-semibold transition-all cursor-pointer",
                        locale === "vi"
                          ? "border-primary bg-primary/10 text-primary shadow-xs font-bold ring-1 ring-primary/30"
                          : "border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                    >
                      <span className="text-sm">🇻🇳</span>
                      <span>{t("settings.langVi")}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setLocale("en" as Locale)}
                      className={cn(
                        "flex items-center justify-center gap-2 rounded-xl border py-2.5 px-3 text-xs font-semibold transition-all cursor-pointer",
                        locale === "en"
                          ? "border-primary bg-primary/10 text-primary shadow-xs font-bold ring-1 ring-primary/30"
                          : "border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                      )}
                    >
                      <span className="text-sm">🇺🇸</span>
                      <span>{t("settings.langEn")}</span>
                    </button>
                  </div>
                </div>
              </section>

              {/* Updates Section */}
              <UpdateSettings />
            </TabsContent>

            {/* TAB 2: LICENSE & ACTIVATION */}
            <TabsContent value="license" className="mt-0 space-y-4">
              <LicenseSettings />
            </TabsContent>

            {/* TAB 3: LOCAL AI & MODELS */}
            <TabsContent value="local-ai" className="mt-0 space-y-4">
              <LocalAiSettings />
            </TabsContent>
          </div>
        </div>
      </Tabs>
    </div>
  )
}

