
import { RefreshCw, Sparkles } from "lucide-react";
import { useTauri } from "@/contexts/tauri-provider";
import { useUpdate } from "@/contexts/update-provider";
import { useTranslation } from "@/hooks/use-translation";
import { Button } from "@/components/ui/button";

export function UpdateSettings() {
  const { isDesktop } = useTauri();
  const { status, currentVersion, availableUpdate, checkForUpdates } = useUpdate();
  const { t } = useTranslation();
  const isChecking = status === "checking";
  const isUpdating = status === "downloading" || status === "installing";

  return (
    <section
      aria-labelledby="updates-heading"
      className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs hover:border-border transition-colors"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3.5 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Sparkles className="h-4.5 w-4.5" />
          </div>
          <div className="min-w-0">
            <h2 id="updates-heading" className="font-bold text-sm sm:text-base text-foreground">
              {t("settings.updatesHeading")}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground flex items-center gap-1.5 flex-wrap">
              <span className="font-medium text-foreground">{t("settings.currentVersion")}</span> ·{" "}
              <output
                aria-label="Current version"
                className="inline-flex items-center rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] font-semibold text-foreground"
              >
                v{currentVersion}
              </output>
            </p>
            <p className="mt-1.5 text-xs sm:text-sm text-muted-foreground" aria-live="polite">
              {!isDesktop && t("settings.desktopOnlyNotice")}
              {isDesktop && status === "up-to-date" && t("settings.upToDate")}
              {isDesktop &&
                status === "available" &&
                availableUpdate &&
                t("settings.updateAvailableReady", {
                  version: availableUpdate.version,
                })}
              {isDesktop && status === "error" && t("settings.updateCheckError")}
              {isDesktop && status === "idle" && t("settings.updateIdleNotice")}
            </p>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!isDesktop || isChecking || isUpdating}
          onClick={() => void checkForUpdates({ interactive: true })}
          className="shrink-0"
          aria-label={
            !isDesktop
              ? t("settings.desktopOnly")
              : isChecking
                ? t("settings.checkingUpdates")
                : undefined
          }
        >
          <RefreshCw
            aria-hidden="true"
            className={`h-3.5 w-3.5 ${isChecking ? "motion-safe:animate-spin" : ""}`}
          />
          <span>
            {!isDesktop
              ? t("settings.desktopOnly")
              : isChecking
                ? t("settings.checkingUpdates")
                : isUpdating
                  ? t("settings.updateInProgress")
                  : t("settings.checkUpdatesBtn")}
          </span>
        </Button>
      </div>
    </section>
  );
}
