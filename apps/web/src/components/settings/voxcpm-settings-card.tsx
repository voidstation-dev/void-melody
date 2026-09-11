import { useCallback, useEffect, useState } from "react"
import { Cpu, Loader2 } from "lucide-react"
import { useTranslation } from "@/hooks/use-translation"
import { toast } from "sonner"
import {
  fetchVoxCpmDownloadProgress,
  fetchVoxCpmInstallation,
  installVoxCpmRuntime,
  removeVoxCpmEnv,
  removeVoxCpmModel,
  verifyVoxCpmInstallation,
  type VoxCpmInstallationInfo,
} from "@/api/voxcpm"

function formatBytes(bytes: number): string {
  if (!bytes) return "0 MB"
  const gb = bytes / 1024 / 1024 / 1024
  const mb = bytes / 1024 / 1024
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${mb.toFixed(0)} MB`
}

function StatusRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl bg-muted/40 px-4 py-3">
      <span className="text-xs font-semibold text-muted-foreground">{label}</span>
      <span className="text-sm font-bold text-foreground">{value}</span>
    </div>
  )
}

/**
 * Phase 10: VoxCPM2 installation card for Settings.
 *
 * Plan separation: this card manages *installation* (worker env, runtime
 * package, model download/remove). Current process/model state lives in the
 * VoxCPM2 Studio Runtime tab, not here.
 */
export function VoxCpmSettingsCard() {
  const { t } = useTranslation()
  const [installation, setInstallation] = useState<VoxCpmInstallationInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      setInstallation(await fetchVoxCpmInstallation())
    } catch {
      setInstallation(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const run = async (
    action: string,
    fn: () => Promise<unknown>,
    successKey: "settings.voxcpmInstallSuccess" | "settings.voxcpmRemoveEnvSuccess" | "settings.voxcpmRemoveModelSuccess",
  ) => {
    setBusy(action)
    try {
      await fn()
      toast.success(t(successKey))
      await load()
    } catch {
      toast.error(t("settings.voxcpmActionError"))
    } finally {
      setBusy(null)
    }
  }

  const handleVerify = async () => {
    setBusy("verify")
    try {
      const result = await verifyVoxCpmInstallation()
      if (result.ok) {
        toast.success(`${t("settings.voxcpmVerifyOk")}${result.version ? ` (${result.version})` : ""}`)
      } else {
        toast.error(result.error || t("settings.voxcpmActionError"))
      }
      await load()
    } catch {
      toast.error(t("settings.voxcpmActionError"))
    } finally {
      setBusy(null)
    }
  }

  if (isLoading && !installation) {
    return (
      <section className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("settings.voxcpmChecking")}
        </div>
      </section>
    )
  }

  const installed = installation?.package_installed ?? false
  const downloaded = installation?.model_status === "downloaded"

  return (
    <section
      aria-labelledby="voxcpm-settings-heading"
      className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs"
    >
      <div className="mb-4 flex items-start gap-3.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Cpu className="h-4.5 w-4.5" />
        </div>
        <div>
          <h2 id="voxcpm-settings-heading" className="font-bold text-sm sm:text-base text-foreground">
            {t("settings.voxcpmHeading")}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">{t("settings.voxcpmSubtitle")}</p>
        </div>
      </div>

      <div className="grid gap-2">
        <StatusRow label={t("settings.voxcpmModel")} value={installation?.model_id ?? "openbmb/VoxCPM2"} />
        <StatusRow
          label={t("settings.voxcpmStatus")}
          value={
            installed && downloaded
              ? t("settings.voxcpmReady")
              : installed
                ? t("settings.voxcpmModelMissing")
                : t("settings.voxcpmNotInstalled")
          }
        />
        <StatusRow label={t("settings.voxcpmStorage")} value={formatBytes(installation?.downloaded_bytes ?? 0)} />
        <StatusRow label={t("settings.voxcpmSampleRate")} value="48 kHz" />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {!installed && (
          <button
            type="button"
            onClick={() => run("install", installVoxCpmRuntime, "settings.voxcpmInstallSuccess")}
            disabled={busy !== null}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-60"
          >
            {busy === "install" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {t("settings.voxcpmInstall")}
          </button>
        )}
        <button
          type="button"
          onClick={handleVerify}
          disabled={busy !== null}
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-2 text-xs font-bold text-foreground transition hover:bg-muted/60 disabled:opacity-60"
        >
          {busy === "verify" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {t("settings.voxcpmVerify")}
        </button>
        {installed && (
          <button
            type="button"
            onClick={() => run("removeEnv", removeVoxCpmEnv, "settings.voxcpmRemoveEnvSuccess")}
            disabled={busy !== null}
            className="inline-flex items-center gap-2 rounded-xl border border-destructive/40 px-4 py-2 text-xs font-bold text-destructive transition hover:bg-destructive/10 disabled:opacity-60"
          >
            {busy === "removeEnv" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {t("settings.voxcpmRemoveEnv")}
          </button>
        )}
        {downloaded && (
          <button
            type="button"
            onClick={() => run("removeModel", removeVoxCpmModel, "settings.voxcpmRemoveModelSuccess")}
            disabled={busy !== null}
            className="inline-flex items-center gap-2 rounded-xl border border-destructive/40 px-4 py-2 text-xs font-bold text-destructive transition hover:bg-destructive/10 disabled:opacity-60"
          >
            {busy === "removeModel" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {t("settings.voxcpmRemoveModel")}
          </button>
        )}
      </div>
    </section>
  )
}