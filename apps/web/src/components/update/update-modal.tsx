"use client";

import { useEffect, useRef } from "react";
import { AlertCircle, Download } from "lucide-react";
import { useUpdate } from "@/contexts/update-provider";
import { useTranslation } from "@/hooks/use-translation";

const WAVE_HEIGHTS = [6, 10, 15, 9, 18, 12, 7, 14, 20, 11, 16, 8, 13, 19, 10, 15, 7, 12];

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
  isVi,
}: {
  downloadedBytes: number;
  totalBytes?: number;
  isVi: boolean;
}) {
  const hasTotal = typeof totalBytes === "number" && totalBytes > 0;
  const ratio = hasTotal ? Math.min(downloadedBytes / totalBytes, 1) : 0;
  const activeSegments = hasTotal ? Math.ceil(ratio * WAVE_HEIGHTS.length) : 0;
  const percentage = hasTotal ? Math.round(ratio * 100) : undefined;

  return (
    <div className="rounded-xl border border-border bg-muted/45 p-4">
      <div
        role="progressbar"
        aria-label={isVi ? "Đang tải bản cập nhật" : "Downloading update"}
        aria-valuemin={hasTotal ? 0 : undefined}
        aria-valuemax={hasTotal ? totalBytes : undefined}
        aria-valuenow={hasTotal ? downloadedBytes : undefined}
        aria-valuetext={hasTotal ? `${percentage}% ${isVi ? "đã tải" : "downloaded"}` : (isVi ? "Đang tải bản cập nhật" : "Downloading update")}
        className={`flex h-7 items-center gap-1 ${hasTotal ? "" : "motion-safe:animate-pulse"}`}
      >
        {WAVE_HEIGHTS.map((height, index) => (
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
        {hasTotal ? `${percentage}%` : (isVi ? "Đang tải bản cập nhật…" : "Downloading update…")}
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
  const { t, locale, isVi } = useTranslation();
  const dialogRef = useRef<HTMLDivElement>(null);
  const primaryActionRef = useRef<HTMLButtonElement>(null);
  const isOpen = ["available", "downloading", "installing", "error"].includes(status);
  const canDismiss = status === "available" || status === "error";

  const title = (() => {
    if (status === "downloading") return isVi ? "Đang tải bản cập nhật" : "Downloading update";
    if (status === "installing") return isVi ? "Đang cài đặt cập nhật" : "Installing update";
    if (status === "error") return isVi ? "Cập nhật gặp sự cố" : "Update could not finish";
    return isVi ? "Đã có bản cập nhật mới" : "Update available";
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
              {status === "available" && (isVi ? "Cài đặt bản cập nhật bất cứ lúc nào. Công việc tạo âm thanh hiện tại của bạn sẽ được giữ nguyên." : "Install the update when you’re ready. Your current audio work stays in place.")}
              {status === "downloading" && (isVi ? "Vui lòng giữ cửa sổ này mở trong khi bản cập nhật đang được tải xuống." : "Keep this window open while the update downloads.")}
              {status === "installing" && (isVi ? "VoidMelody sẽ đóng trong giây lát và tự khởi động lại khi cập nhật hoàn tất." : "VoidMelody will close briefly and reopen when the update is ready.")}
              {status === "error" && (errorMessage ?? (isVi ? "Không thể hoàn tất cập nhật. Vui lòng thử lại." : "The update could not be completed. Try again."))}
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
                {isVi ? `Phát hành ${formatReleaseDate(availableUpdate.date, locale)}` : `Released ${formatReleaseDate(availableUpdate.date, locale)}`}
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
            <DownloadProgress downloadedBytes={downloadedBytes} totalBytes={totalBytes} isVi={isVi} />
          </div>
        )}

        {status === "installing" && (
          <div className="mt-6 rounded-xl border border-border bg-muted/45 px-4 py-3 text-sm font-semibold" aria-live="polite">
            {isVi ? "Đang cài đặt bản cập nhật…" : "Installing update…"}
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
                {isVi ? "Để sau" : "Later"}
              </button>
              <button
                ref={primaryActionRef}
                type="button"
                onClick={() => void installAvailableUpdate()}
                className="min-h-10 touch-manipulation rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors motion-reduce:transition-none hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {isVi ? "Cập nhật ngay" : "Update now"}
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
                {isVi ? "Đóng" : "Not now"}
              </button>
              <button
                ref={primaryActionRef}
                type="button"
                onClick={() => void checkForUpdates({ interactive: true })}
                className="min-h-10 touch-manipulation rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors motion-reduce:transition-none hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {isVi ? "Thử lại" : "Try again"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
