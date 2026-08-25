import { useRef, useState } from "react"
import { Cpu, HardDrive, Loader2, Package, RotateCcw, Trash2, Wrench } from "lucide-react"
import { useRuntimes } from "@/hooks/use-runtimes"
import { useTranslation } from "@/hooks/use-translation"
import { toast } from "sonner"
import { SpeechModelSelector } from "./speech-model-selector"

function formatBytes(bytes: number): string {
  if (!bytes) return "0 MB"
  const gb = bytes / 1024 / 1024 / 1024
  const mb = bytes / 1024 / 1024
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${mb.toFixed(0)} MB`
}

function statusLabel(status: string, t: (k: string) => string): string {
  switch (status) {
    case "ready":
      return t("settings.localAiReady")
    case "missing":
      return t("settings.localAiNotInstalled")
    case "downloading":
      return t("settings.localAiDownloading")
    case "verifying":
      return t("settings.localAiVerifying")
    case "installing":
      return t("settings.localAiInstalling")
    case "error":
      return t("settings.localAiError")
    case "update_required":
      return t("settings.localAiUpdateRequired")
    default:
      return status
  }
}

function RuntimeCard({
  id,
  title,
  description,
}: {
  id: string
  title: string
  description: string
}) {
  const { t } = useTranslation()
  const { query, install, update, repair, remove, rollback } = useRuntimes()
  const state = query.data?.find((s) => s.id === id)
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const updateRef = useRef<HTMLInputElement>(null)

  const isReady = state?.status === "ready"
  const isMissing = !state || state.status === "missing"
  const hasError = state?.status === "error"

  const handleInstall = async (file: File) => {
    setBusy(true)
    try {
      await install.mutateAsync({ id, file })
      toast.success(t("settings.localAiInstallSuccess"))
    } catch {
      toast.error(t("settings.localAiInstallError"))
    } finally {
      setBusy(false)
    }
  }

  const handleUpdate = async (file: File) => {
    setBusy(true)
    try {
      await update.mutateAsync({ id, file })
      toast.success(t("settings.localAiUpdateSuccess"))
    } catch {
      toast.error(t("settings.localAiInstallError"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-bold">{title}</h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
            isReady
              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
              : isMissing
                ? "bg-muted text-muted-foreground"
                : hasError
                  ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400"
                  : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
          }`}
        >
          {state ? statusLabel(state.status, t) : t("settings.localAiNotInstalled")}
        </span>
      </div>

      {state?.activeVersion && (
        <p className="mt-2 text-xs text-muted-foreground">
          {t("settings.localAiVersion")}{" "}
          <span className="font-mono font-semibold text-foreground">{state.activeVersion}</span>
        </p>
      )}

      {state?.diskUsageBytes > 0 && (
        <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
          <HardDrive className="h-3 w-3" />
          {formatBytes(state.diskUsageBytes)}
        </p>
      )}

      {state?.error && (
        <p className="mt-2 text-xs font-semibold text-destructive">{state.error}</p>
      )}

      <input
        ref={fileRef}
        type="file"
        accept=".zip"
        className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) void handleInstall(f)
          e.target.value = ""
        }}
      />
      <input
        ref={updateRef}
        type="file"
        accept=".zip"
        className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) void handleUpdate(f)
          e.target.value = ""
        }}
      />

      <div className="mt-3 flex flex-wrap gap-2">
        {isMissing && (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground disabled:opacity-40"
          >
            {busy && <Loader2 className="h-3 w-3 animate-spin" />}
            {t("settings.localAiInstall")}
          </button>
        )}
        {isReady && (
          <>
            <button
              type="button"
              onClick={() => updateRef.current?.click()}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-40"
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Cpu className="h-3 w-3" />}
              {t("settings.localAiUpdate")}
            </button>
            <button
              type="button"
              onClick={() => void repair.mutateAsync(id)}
              disabled={repair.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-40"
            >
              {repair.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Wrench className="h-3 w-3" />}
              {t("settings.localAiRepair")}
            </button>
            <button
              type="button"
              onClick={() => void remove.mutateAsync(id)}
              disabled={remove.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 hover:bg-red-100 dark:border-red-900 dark:bg-red-950/40 dark:text-red-400 disabled:opacity-40"
            >
              {remove.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
              {t("settings.localAiRemove")}
            </button>
          </>
        )}
        {hasError && state?.installedVersions && state.installedVersions.length > 1 && (
          <button
            type="button"
            onClick={() => void rollback.mutateAsync(id)}
            disabled={rollback.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-40"
          >
            {rollback.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <RotateCcw className="h-3 w-3" />}
            {t("settings.localAiRollback")}
          </button>
        )}
      </div>
    </div>
  )
}

export function LocalAiSettings() {
  const { t } = useTranslation()
  return (
    <section
      aria-labelledby="local-ai-heading"
      className="rounded-2xl border border-border/80 bg-card p-5 sm:p-6 shadow-xs"
    >
      <div className="mb-4 flex items-start gap-3.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Cpu className="h-4.5 w-4.5" />
        </div>
        <div>
          <h2 id="local-ai-heading" className="font-bold text-sm sm:text-base text-foreground">
            {t("settings.localAiHeading")}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">{t("settings.localAiSubtitle")}</p>
        </div>
      </div>
      <div className="space-y-4">
        <RuntimeCard
          id="vieneu"
          title={t("settings.localAiVieneuTitle")}
          description={t("settings.localAiVieneuDesc")}
        />
        <SpeechModelSelector />
      </div>
    </section>
  )
}