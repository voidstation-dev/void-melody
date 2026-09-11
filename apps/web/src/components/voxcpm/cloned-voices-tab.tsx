import { useEffect } from "react"
import { useTranslation } from "@/hooks/use-translation"
import { useVoxCpmStore } from "@/stores/voxcpm-store"
import { Loader2, Mic } from "lucide-react"

/** Phase 1: cloned voice list rendered from mock data (real storage lands in Phase 3). */
export function ClonedVoicesTab() {
  const { t } = useTranslation()
  const clonedVoices = useVoxCpmStore((s) => s.clonedVoices)
  const isLoadingVoices = useVoxCpmStore((s) => s.isLoadingVoices)
  const voicesError = useVoxCpmStore((s) => s.voicesError)
  const loadClonedVoices = useVoxCpmStore((s) => s.loadClonedVoices)
  const setSelectedVoiceId = useVoxCpmStore((s) => s.setSelectedVoiceId)

  useEffect(() => {
    void loadClonedVoices()
  }, [loadClonedVoices])

  if (isLoadingVoices) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("common.loading")}
      </div>
    )
  }

  if (voicesError) {
    return <div className="p-6 text-sm text-destructive">{voicesError}</div>
  }

  if (clonedVoices.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-border bg-card p-10 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
          <Mic className="h-6 w-6 text-primary" />
        </div>
        <h2 className="text-base font-bold">{t("voxcpm.noVoicesYet")}</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          {t("voxcpm.voicesComingSoonDesc")}
        </p>
      </section>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {clonedVoices.map((voice) => (
        <article
          key={voice.id}
          className="rounded-2xl border border-border bg-card p-5 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
              <Mic className="h-5 w-5 text-primary" />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-bold">{voice.display_name}</h3>
              <p className="text-xs text-muted-foreground">
                {t("voxcpm.referenceDuration")}: {voice.reference_duration_seconds.toFixed(1)}s · {voice.sample_rate / 1000} kHz
              </p>
            </div>
          </div>
          {voice.description ? (
            <p className="mt-3 line-clamp-2 text-xs text-muted-foreground">{voice.description}</p>
          ) : null}
          <button
            type="button"
            onClick={() => setSelectedVoiceId(voice.id)}
            className="mt-4 w-full rounded-xl bg-primary/10 px-3 py-2 text-xs font-bold text-primary transition-all hover:bg-primary/15"
          >
            {t("voxcpm.useVoice")}
          </button>
        </article>
      ))}
    </div>
  )
}