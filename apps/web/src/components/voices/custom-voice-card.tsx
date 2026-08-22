"use client"

import { useState } from "react"
import { CustomVoice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { providerLabel } from "./voice-library-utils"
import { VoiceActionsMenu } from "./voice-actions-menu"
import { VoiceDeleteDialog } from "./voice-delete-dialog"
import { VoicePreviewButton } from "./voice-preview-button"
import { VoiceWaveform } from "./voice-waveform"

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
    <article className="group relative flex min-h-[300px] flex-col rounded-[1.25rem] border-2 border-blue-500 bg-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md motion-reduce:transform-none sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-[#df604e]">{t("voices.customEyebrow")}</p>
          <h3 className="mt-4 text-2xl font-black tracking-[-0.045em] text-foreground">{voice.display_name}</h3>
          <p className="mt-2 text-sm leading-5 text-muted-foreground">{t("voices.customDescription")}</p>
        </div>
        <VoiceActionsMenu voiceId={voice.id} onDelete={() => setDeleteOpen(true)} disabled={deleting} />
      </div>

      <div className="mt-auto">
        <div className="mt-6 flex items-center gap-4">
          <VoicePreviewButton
            voiceId={voice.id}
            label={voice.display_name}
            sampleText={voice.transcript || t("voices.sampleText", { name: voice.display_name })}
            variant="custom"
            compact
          />
          <VoiceWaveform accent="coral" />
          <span className="ml-auto text-sm font-medium tabular-nums text-muted-foreground">{durationLabel}</span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm font-medium text-muted-foreground">
          {metadata.map((item, index) => (
            <span
              key={item}
              className={index > 0 ? "relative pl-3 before:absolute before:left-0 before:top-1/2 before:h-1 before:w-1 before:-translate-y-1/2 before:rounded-full before:bg-muted-foreground/50" : undefined}
            >
              {item}
            </span>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between gap-4 border-t border-border pt-4">
          <a
            href={`/?voice=${encodeURIComponent(voice.id)}`}
            className="inline-flex items-center text-base font-black tracking-tight text-foreground transition-colors hover:text-[#df604e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            title={t("voices.useVoiceTitle")}
          >
            {t("voices.useVoice")} <span className="ml-2 text-[#df604e]">→</span>
          </a>
          <span className="text-xs font-medium text-muted-foreground">{t("voices.customReadyHint")}</span>
        </div>
      </div>
      <VoiceDeleteDialog open={deleteOpen} voiceName={voice.display_name} pending={deleting} onCancel={() => setDeleteOpen(false)} onConfirm={() => onDelete(voice.id)} />
    </article>
  )
}
