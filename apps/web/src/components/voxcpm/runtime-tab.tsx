import { useEffect } from "react"
import { useTranslation } from "@/hooks/use-translation"
import { useVoxCpmStore } from "@/stores/voxcpm-store"
import { VOXCPM2_PROVIDER_ID } from "@/types/voxcpm"
import { VoxCpmRuntimeBadge } from "./voxcpm-runtime-badge"
import { Loader2 } from "lucide-react"

function RuntimeRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl bg-muted/40 px-4 py-3">
      <span className="text-xs font-semibold text-muted-foreground">{label}</span>
      <span className="text-sm font-bold text-foreground">{value}</span>
    </div>
  )
}

/** Phase 1: runtime tab fed by mock runtime info (real worker lands in Phase 2). */
export function RuntimeTab() {
  const { t } = useTranslation()
  const runtime = useVoxCpmStore((s) => s.runtime)
  const isLoadingRuntime = useVoxCpmStore((s) => s.isLoadingRuntime)
  const runtimeError = useVoxCpmStore((s) => s.runtimeError)
  const loadRuntime = useVoxCpmStore((s) => s.loadRuntime)

  useEffect(() => {
    void loadRuntime()
  }, [loadRuntime])

  if (isLoadingRuntime && !runtime) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("voxcpm.runtimeChecking")}
      </div>
    )
  }

  if (runtimeError && !runtime) {
    return <div className="p-6 text-sm text-destructive">{runtimeError}</div>
  }

  if (!runtime) return null

  const statusLabel =
    runtime.status === "ready"
      ? t("voxcpm.runtimeBadgeReady")
      : runtime.status === "broken"
        ? t("voxcpm.runtimeBadgeBroken")
        : t("voxcpm.runtimeBadgeNotInstalled")

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-base font-bold">{t("voxcpm.tabRuntime")}</h2>
          <VoxCpmRuntimeBadge runtime={runtime} />
        </div>
        <div className="grid gap-2">
          <RuntimeRow label={t("voxcpm.worker")} value={runtime.worker_running ? "Running" : "Stopped"} />
          <RuntimeRow label={t("voxcpm.model")} value={runtime.model_loaded ? "Loaded" : "Not loaded"} />
          <RuntimeRow label={t("voxcpm.device")} value={runtime.device} />
          <RuntimeRow label={t("voxcpm.sampleRate")} value={`${(runtime.sample_rate / 1000).toFixed(0)} kHz`} />
          <RuntimeRow label={t("voxcpm.backend")} value={runtime.backend} />
          <RuntimeRow label={t("voxcpm.status")} value={VOXCPM2_PROVIDER_ID} />
        </div>
      </section>
      <p className="px-1 text-xs text-muted-foreground">{t("voxcpm.voicesComingSoonDesc")}</p>
    </div>
  )
}