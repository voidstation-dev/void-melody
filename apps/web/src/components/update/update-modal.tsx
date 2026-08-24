
import { useEffect, useRef } from "react";
import { AlertCircle, Download } from "lucide-react";
import { useUpdate } from "@/contexts/update-provider";
import { useTranslation } from "@/hooks/use-translation";
import { DEFAULT_WAVE_HEIGHTS } from "@/constants";

function formatReleaseDate(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  }).format(new Date(value));
}

function DownloadProgress({
  downloadedBytes,
  totalBytes,
}: {
  downloadedBytes: number;
  totalBytes?: number;
}) {
  const { t } = useTranslation();
  const hasTotal = typeof totalBytes === "number" && totalBytes > 0;
  const ratio = hasTotal ? Math.min(downloadedBytes / totalBytes, 1) : 0;
  const activeSegments = hasTotal ? Math.ceil(ratio * DEFAULT_WAVE_HEIGHTS.length) : 0;
  const percentage = hasTotal ? Math.round(ratio * 100) : undefined;

  return (
    <div className="rounded-xl border border-border bg-muted/45 p-4">
      <div
        role="progressbar"
        aria-label={t("update.ariaDownloading")}
        aria-valuemin={hasTotal ? 0 : undefined}
        aria-valuemax={hasTotal ? totalBytes : undefined}
        aria-valuenow={hasTotal ? downloadedBytes : undefined}
        aria-valuetext={hasTotal ? `${percentage}% ${t("update.ariaDownloaded")}` : t("update.ariaDownloading")}
        className={`flex h-7 items-center gap-1 ${hasTotal ? "" : "motion-safe:animate-pulse"}`}
      >
        {DEFAULT_WAVE_HEIGHTS.map((height, index) => (
          <span
            key={`${height}-${index}`}
            aria-hidden="true"
            className={`min-w-0 flex-1 rounded-full transition-colors motion-reduce:transition-none ${
              hasTotal && index < activeSegments ? "bg-primary" : "bg-border"
            }`}
            style={{ height }}
          />
        ))}
      </div>
      <p className="mt-2 text-xs font-semibold tabular-nums text-muted-foreground" aria-live="polite">
        {hasTotal ? `${percentage}%` : t("update.downloadingUpdate")}
      </p>
    </div>
  );
}

export function UpdateModal() {
  const {
    status,
    availableUpdate,
    downloadedBytes,
    totalBytes,
    errorMessage,
    checkForUpdates,
    installAvailableUpdate,
    dismissUpdate,
  } = useUpdate();
  const { t, locale } = useTranslation();
  const dialogRef = useRef<HTMLDivElement>(null);
  const primaryActionRef = useRef<HTMLButtonElement>(null);
  const isOpen = ["available", "downloading", "installing", "error"].includes(status);
  const canDismiss = status === "available" || status === "error";

  const title = (() => {
    if (status === "downloading") return t("update.statusDownloading");
    if (status === "installing") return t("update.statusInstalling");
    if (status === "error") return t("update.statusError");
    return t("update.statusAvailable");
  })();

  useEffect(() => {
    if (!isOpen) return;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    (primaryActionRef.current ?? dialogRef.current)?.focus();
    return () => {
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, [isOpen, status]);

  if (!isOpen) return null;

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && canDismiss) {
      event.preventDefault();
      void dismissUpdate();
      return;
    }
    if (event.key !== "Tab") return;

    const buttons = Array.from(
      dialogRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? [],
    );
    if (buttons.length === 0) {
      event.preventDefault();
      dialogRef.current?.focus();
      return;
    }
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 p-4 sm:p-6">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="update-dialog-title"
        aria-describedby="update-dialog-description"
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="max-h-[min(42rem,calc(100vh-2rem))] w-full max-w-lg overscroll-contain overflow-y-auto rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-2xl outline-none sm:p-7"
      >
        <div className="flex items-start gap-4">
          <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
            {status === "error" ? (
              <AlertCircle aria-hidden="true" className="h-5 w-5" />
            ) : (
              <Download aria-hidden="true" className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h2 id="update-dialog-title" className="text-balance text-xl font-bold tracking-tight">
              {title}
            </h2>
            <p id="update-dialog-description" className="mt-1 text-sm leading-6 text-muted-foreground">
              {status === "available" && t("update.descAvailable")}
              {status === "downloading" && t("update.descDownloading")}
              {status === "installing" && t("update.descInstalling")}
              {status === "error" && (errorMessage ?? t("update.descError"))}
            </p>
          </div>
        </div>

        {availableUpdate && (status === "available" || status === "error") && (
          <div className="mt-6 break-words rounded-xl border border-border bg-background p-4">
            <p className="text-sm font-bold" translate="no">
              v{availableUpdate.currentVersion} → v{availableUpdate.version}
            </p>
            {availableUpdate.date && (
              <p className="mt-1 text-xs text-muted-foreground">
                {t("update.releasedDate", { date: formatReleaseDate(availableUpdate.date, locale) })}
              </p>
            )}
            {availableUpdate.notes && (
              <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-6 text-muted-foreground">
                {availableUpdate.notes}
              </p>
            )}
          </div>
        )}

        {status === "downloading" && (
          <div className="mt-6">
            <DownloadProgress downloadedBytes={downloadedBytes} totalBytes={totalBytes} />
          </div>
        )}

        {status === "installing" && (
          <div className="mt-6 rounded-xl border border-border bg-muted/45 px-4 py-3 text-sm font-semibold" aria-live="polite">
            {t("update.installingUpdate")}
          </div>
        )}

        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          {status === "available" && (
            <>
              <button
                type="button"
                onClick={() => void dismissUpdate()}
                className="min-h-10 touch-manipulation rounded-lg border border-border bg-background px-4 py-2 text-sm font-semibold transition-colors motion-reduce:transition-none hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {t("update.later")}
              </button>
              <button
                ref={primaryActionRef}
                type="button"
                onClick={() => void installAvailableUpdate()}
                className="min-h-10 touch-manipulation rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors motion-reduce:transition-none hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {t("update.updateNow")}
              </button>
            </>
          )}
          {status === "error" && (
            <>
              <button
                type="button"
                onClick={() => void dismissUpdate()}
                className="min-h-10 touch-manipulation rounded-lg border border-border bg-background px-4 py-2 text-sm font-semibold transition-colors motion-reduce:transition-none hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {t("update.notNow")}
              </button>
              <button
                ref={primaryActionRef}
                type="button"
                onClick={() => void checkForUpdates({ interactive: true })}
                className="min-h-10 touch-manipulation rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors motion-reduce:transition-none hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {t("update.tryAgain")}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
