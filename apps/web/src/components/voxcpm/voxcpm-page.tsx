import { useEffect } from "react"
import { useSearch } from "@tanstack/react-router"
import { useTranslation } from "@/hooks/use-translation"
import { useVoxCpmStore } from "@/stores/voxcpm-store"
import { VoxCpmTabs } from "./voxcpm-tabs"
import { VoxCpmRuntimeBadge } from "./voxcpm-runtime-badge"

/** VoxCPM2 Studio page shell (Phase 1 — mock data, isolated from VieNeu). */
export function VoxCpmPage() {
  const { t } = useTranslation()
  const loadRuntime = useVoxCpmStore((s) => s.loadRuntime)
  const runtime = useVoxCpmStore((s) => s.runtime)
  const isLoadingRuntime = useVoxCpmStore((s) => s.isLoadingRuntime)
  const loadClonedVoices = useVoxCpmStore((s) => s.loadClonedVoices)
  const setSelectedVoiceId = useVoxCpmStore((s) => s.setSelectedVoiceId)

  useEffect(() => {
    if (!runtime && !isLoadingRuntime) void loadRuntime()
  }, [runtime, isLoadingRuntime, loadRuntime])

  // Phase 7: shared Voice Library deep-links ?voice=<id> here; select it and
  // open the emotional TTS tab.
  const search = useSearch({ from: "/voxcpm", shouldThrow: false }) as
    { voice?: string } | undefined
  const linkedVoiceId = search?.voice ?? null

  useEffect(() => {
    if (!linkedVoiceId) return
    void loadClonedVoices().then(() => {
      setSelectedVoiceId(linkedVoiceId)
    })
  }, [linkedVoiceId, loadClonedVoices, setSelectedVoiceId])

  return (
    <div className="flex flex-1 flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-extrabold tracking-tight">{t("voxcpm.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("voxcpm.subtitle")}</p>
        </div>
        <VoxCpmRuntimeBadge runtime={runtime} />
      </header>
      <VoxCpmTabs />
    </div>
  )
}