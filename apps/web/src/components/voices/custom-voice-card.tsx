import { useState } from "react"
import { CustomVoice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { providerLabel } from "./voice-library-utils"
import { VoiceActionsMenu } from "./voice-actions-menu"
import { VoiceDeleteDialog } from "./voice-delete-dialog"
import { VoicePreviewButton } from "./voice-preview-button"
import { VoiceWaveform } from "./voice-waveform"
import { UserCheck, ArrowRight } from "lucide-react"

type CustomVoiceCardProps = { voice: CustomVoice; onDelete: (voiceId: string) => void; deleting?: boolean }

export function CustomVoiceCard({ voice, onDelete, deleting = false }: CustomVoiceCardProps) {
  const { t } = useTranslation()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const duration = voice.reference_duration_seconds ?? voice.duration_seconds
  const durationLabel = duration != null ? `0:${String(Math.round(duration)).padStart(2, "0")}` : t("voices.previewDuration")
  const metadata = [
    providerLabel(voice.provider_id),
    voice.quality_score != null ? t("voices.customQuality", { score: voice.quality_score }) : null,
    voice.status === "ready" ? t("voices.customReadyStatus") : voice.status,
  ].filter(Boolean) as string[]

  return (
    <article className="group relative flex min-h-[220px] flex-col justify-between rounded-2xl border border-primary/20 bg-card p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md motion-reduce:transform-none">
      {/* Top Section */}
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                <UserCheck className="h-2.5 w-2.5" />
                {t("voices.customEyebrow")}
              </span>
            </div>

            <h3 className="mt-2 text-2xl font-black tracking-tight text-foreground group-hover:text-primary transition-colors truncate">
              {voice.display_name}
            </h3>
          </div>

          <VoiceActionsMenu voiceId={voice.id} onDelete={() => setDeleteOpen(true)} disabled={deleting} />
        </div>
      </div>

      {/* Audio Player Strip */}
      <div className="my-3 flex items-center gap-2.5 rounded-xl border border-border/50 bg-muted/20 px-2.5 py-2 transition-colors group-hover:bg-muted/40">
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
          <span className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
            {durationLabel}
          </span>
        </div>
      </div>

      {/* Footer Strip */}
      <div className="flex items-center justify-between gap-3 border-t border-border/50 pt-2.5">
        <div className="flex flex-wrap items-center gap-x-2 text-[11px] font-medium text-muted-foreground">
          {metadata.map((item, index) => (
            <span
              key={item}
              className={index > 0 ? "relative pl-2.5 before:absolute before:left-0 before:top-1/2 before:h-1 before:w-1 before:-translate-y-1/2 before:rounded-full before:bg-muted-foreground/30" : undefined}
            >
              {item}
            </span>
          ))}
        </div>

        <a
          href={`/?voice=${encodeURIComponent(voice.id)}`}
          className="shrink-0 inline-flex items-center gap-1 text-xs font-bold text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          title={t("voices.useVoiceTitle")}
        >
          <span>{t("voices.useVoice")}</span>
          <ArrowRight className="h-3.5 w-3.5 text-primary transition-transform group-hover:translate-x-0.5" />
        </a>
      </div>

      <VoiceDeleteDialog open={deleteOpen} voiceName={voice.display_name} pending={deleting} onCancel={() => setDeleteOpen(false)} onConfirm={() => onDelete(voice.id)} />
    </article>
  )
}
