import { useTranslation } from "@/hooks/use-translation"
import type { VoxCpmRuntimeInfo } from "@/types/voxcpm"

/**
 * Runtime status badge, styled after the existing VieneuPage RuntimeBadge
 * (semantic emerald/amber states, rounded-full pill, no provider colors).
 */
export function VoxCpmRuntimeBadge({ runtime }: { runtime: VoxCpmRuntimeInfo | null }) {
  const { t } = useTranslation()

  if (!runtime) {
    return (
      <span className="rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground">
        {t("voxcpm.runtimeChecking")}
      </span>
    )
  }

  const available = runtime.status === "ready"
  const label =
    runtime.status === "ready"
      ? t("voxcpm.runtimeBadgeReady")
      : runtime.status === "broken"
        ? t("voxcpm.runtimeBadgeBroken")
        : t("voxcpm.runtimeBadgeNotInstalled")

  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold ${available ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400" : "border-amber-200 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"}`}
      title={runtime.reason ?? undefined}
    >
      <span
        className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${available ? "bg-emerald-500" : "bg-amber-500"}`}
      />
      {label}
    </span>
  )
}