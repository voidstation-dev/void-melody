
import { RefreshCcw } from "lucide-react"
import { Voice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { PresetVoiceRow } from "./preset-voice-row"
import { VoiceLibraryEmpty } from "./voice-library-empty"
import { VoiceLibrarySkeleton } from "./voice-library-skeleton"

type PresetVoicesSectionProps = { voices: Voice[]; isLoading: boolean; isError: boolean; hasFilters: boolean; onRetry: () => void }

export function PresetVoicesSection({ voices, isLoading, isError, hasFilters, onRetry }: PresetVoicesSectionProps) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="preset-voices-heading" className="space-y-4">
      <div><h2 id="preset-voices-heading" className="text-lg font-black tracking-tight">{t("voices.presetHeading")}</h2><p className="mt-1 text-sm text-muted-foreground">{t("voices.presetSectionDescription")}</p></div>
      {isLoading ? <VoiceLibrarySkeleton variant="preset" /> : isError ? <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-5 py-6 text-sm"><p className="font-bold text-destructive">{t("voices.presetLoadError")}</p><button type="button" onClick={onRetry} className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-destructive underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><RefreshCcw className="h-3.5 w-3.5" />{t("common.retry")}</button></div> : voices.length === 0 ? <VoiceLibraryEmpty kind={hasFilters ? "search" : "preset"} /> : <div className="grid gap-3 lg:grid-cols-2">{voices.map((voice) => <PresetVoiceRow key={voice.voiceType} voice={voice} />)}</div>}
    </section>
  )
}
