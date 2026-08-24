
import React from "react";
import { KeyRound, CheckCircle2, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useTranslation } from "@/hooks/use-translation";

function maskKey(key: string | null): string {
  if (!key) return "—";
  if (key.length <= 4) return "****";
  const start = key.slice(0, 3);
  const end = key.slice(-2);
  return `${start}****${end}`;
}

export function LicenseSettings() {
  const { licenseKey, licenseInfo, logout } = useAuth();
  const { t } = useTranslation();

  const handleLogout = () => {
    if (window.confirm(t("auth.logoutConfirm"))) {
      logout();
    }
  };

  return (
    <section aria-labelledby="license-heading" className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 id="license-heading" className="font-bold text-base text-foreground">
              {t("auth.licenseStatus")}
            </h2>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {t("auth.licenseActive")}
            </span>
          </div>
          
          <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">{t("auth.licenseOwner")}:</span>{" "}
              {licenseInfo?.ownerName ?? "Phong Vũ"} ({licenseInfo?.tier ?? "Lifetime Pro License"})
            </p>
            <p className="flex items-center gap-1.5">
              <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">
                {maskKey(licenseKey)}
              </code>
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="inline-flex min-h-10 shrink-0 touch-manipulation items-center justify-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2 text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive focus-visible:ring-offset-2"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>{t("auth.logoutBtn")}</span>
        </button>
      </div>
    </section>
  );
}
