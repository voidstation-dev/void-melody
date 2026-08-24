import { useState } from "react"
import { CustomVoice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { providerLabel } from "./voice-library-utils"
import { VoiceActionsMenu } from "./voice-actions-menu"
import { VoiceDeleteDialog } from "./voice-delete-dialog"
import { VoicePreviewButton } from "./voice-preview-button"
import { VoiceWaveform } from "./voice-waveform"
import { ArrowRight } from "lucide-react"

type CustomVoiceCardProps = { voice: CustomVoice; onDelete: (voiceId: string) => void; deleting?: boolean }

export function CustomVoiceCard({ voice, onDelete, deleting = false }: CustomVoiceCardProps) {
  const { t } = useTranslation()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const duration = voice.reference_duration_seconds ?? voice.duration_seconds
  const durationLabel = duration != null ? `0:${String(Math.round(duration)).padStart(2, "0")}` : t("voices.previewDuration")

  return (
    <article className="group relative flex flex-col justify-between rounded-xl border border-border/70 bg-card p-3 sm:p-3.5 shadow-2xs transition-all duration-200 hover:border-primary/50 hover:shadow-xs">
      {/* Header: Title + Meta & Actions */}
      <div className="flex items-start justify-between gap-2.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors truncate">
              {voice.display_name}
            </h3>
            <span className="shrink-0 rounded-md bg-violet-500/15 px-1.5 py-0.2 text-[9px] font-black uppercase text-violet-600 dark:text-violet-400">
              Clone
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5 truncate">
            <span>{providerLabel(voice.provider_id)}</span>
            {voice.quality_score != null && (
              <>
                <span className="text-muted-foreground/40">•</span>
                <span>{t("voices.customQuality", { score: voice.quality_score })}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <a
            href={`/?voice=${encodeURIComponent(voice.id)}`}
            className="inline-flex items-center gap-1 rounded-lg bg-primary/10 hover:bg-primary text-primary hover:text-primary-foreground px-2.5 py-1 text-[11px] font-bold transition-all shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-95"
            title={t("voices.useVoiceTitle")}
          >
            <span>{t("voices.useVoice")}</span>
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </a>

          <VoiceActionsMenu voiceId={voice.id} onDelete={() => setDeleteOpen(true)} disabled={deleting} />
        </div>
      </div>

      {/* Slim Audio Waveform Strip */}
      <div className="mt-2.5 flex items-center gap-2 rounded-lg border border-border/50 bg-muted/25 px-2 py-1.5 transition-colors group-hover:bg-muted/40">
        <VoicePreviewButton
          voiceId={voice.id}
          label={voice.display_name}
          sampleText={voice.transcript || t("voices.sampleText", { name: voice.display_name })}
          variant="custom"
          compact
          size="sm"
        />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-2 overflow-hidden">
          <VoiceWaveform accent="coral" />
          <span className="shrink-0 text-[10px] font-mono font-medium tabular-nums text-muted-foreground">
            {durationLabel}
          </span>
        </div>
      </div>

      <VoiceDeleteDialog open={deleteOpen} voiceName={voice.display_name} pending={deleting} onCancel={() => setDeleteOpen(false)} onConfirm={() => onDelete(voice.id)} />
    </article>
  )
}
