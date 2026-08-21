"use client";

import { RefreshCw } from "lucide-react";
import { useTauri } from "@/contexts/tauri-provider";
import { useUpdate } from "@/contexts/update-provider";
import { useTranslation } from "@/hooks/use-translation";

export function UpdateSettings() {
  const { isDesktop } = useTauri();
  const { status, currentVersion, availableUpdate, checkForUpdates } = useUpdate();
  const { t, isVi } = useTranslation();
  const isChecking = status === "checking";
  const isUpdating = status === "downloading" || status === "installing";

  return (
    <section aria-labelledby="updates-heading" className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2 id="updates-heading" className="font-bold text-base text-foreground">
            {t("settings.updatesHeading")}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{t("settings.currentVersion")}</span> ·{" "}
            <output aria-label="Current version">v{currentVersion}</output>
          </p>
          <p className="mt-2 text-sm text-muted-foreground" aria-live="polite">
            {!isDesktop && (isVi ? "Tính năng cập nhật chỉ khả dụng trên ứng dụng Desktop." : "Updates are available in the desktop app.")}
            {isDesktop && status === "up-to-date" && (isVi ? "Ứng dụng đang ở phiên bản mới nhất." : "You’re up to date.")}
            {isDesktop && status === "available" && availableUpdate &&
              (isVi ? `Phiên bản ${availableUpdate.version} đã sẵn sàng.` : `Version ${availableUpdate.version} is ready.`)}
            {isDesktop && status === "error" && (isVi ? "Kiểm tra cập nhật gặp sự cố." : "The update check needs attention.")}
            {isDesktop && status === "idle" && (isVi ? "Kiểm tra bất cứ lúc nào. Công việc tạo âm thanh của bạn sẽ không bị gián đoạn." : "Check when you’re ready. Your audio work stays open.")}
          </p>
        </div>

        <button
          type="button"
          disabled={!isDesktop || isChecking || isUpdating}
          onClick={() => void checkForUpdates({ interactive: true })}
          className="inline-flex min-h-10 shrink-0 touch-manipulation items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 py-2 text-sm font-semibold text-foreground transition-colors motion-reduce:transition-none hover:bg-muted disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          aria-label={!isDesktop ? "Desktop app only" : isChecking ? (isVi ? "Đang kiểm tra cập nhật" : "Checking for updates") : undefined}
        >
          <RefreshCw
            aria-hidden="true"
            className={`h-4 w-4 ${isChecking ? "motion-safe:animate-spin" : ""}`}
          />
          {!isDesktop
            ? (isVi ? "Chỉ dành cho Desktop" : "Desktop app only")
            : isChecking
              ? (isVi ? "Đang kiểm tra…" : "Checking…")
              : isUpdating
                ? (isVi ? "Đang cập nhật…" : "Update in progress")
                : (isVi ? "Kiểm tra cập nhật" : "Check for updates")}
        </button>
      </div>
    </section>
  );
}
