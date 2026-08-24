
import React from "react";
import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useTranslation } from "@/hooks/use-translation";
import { Button } from "@/components/ui/button";

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
    <section
      aria-labelledby="license-heading"
      className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs hover:border-border transition-colors"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3.5 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="h-4.5 w-4.5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 id="license-heading" className="font-bold text-sm sm:text-base text-foreground">
                {t("auth.licenseStatus")}
              </h2>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {t("auth.licenseActive")}
              </span>
            </div>

            <div className="mt-2 space-y-1 text-xs text-muted-foreground">
              <p>
                <span className="font-medium text-foreground">{t("auth.licenseOwner")}:</span>{" "}
                {licenseInfo?.ownerName ?? "Phong Vũ"} ({licenseInfo?.tier ?? "Lifetime Pro License"})
              </p>
              <div className="flex items-center gap-1.5">
                <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">
                  {maskKey(licenseKey)}
                </code>
              </div>
            </div>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleLogout}
          className="shrink-0 border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>{t("auth.logoutBtn")}</span>
        </Button>
      </div>
    </section>
  );
}
