"use client"

import Link from "next/link"
import { Voice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { providerLabel } from "./voice-library-utils"
import { VoicePreviewButton } from "./voice-preview-button"
import { VoiceWaveform } from "./voice-waveform"

export function PresetVoiceRow({ voice, onPlayStart }: { voice: Voice; onPlayStart?: (voiceId: string) => void }) {
  const { t } = useTranslation()
  const sampleText = t("voices.sampleSentence", { name: voice.displayName })
  const metadata = [providerLabel(voice.providerId), t("voices.presetMetaStyle"), t("voices.presetMetaPopularity")]

  return (
    <article className="group flex min-h-[300px] flex-col rounded-[1.25rem] border-2 border-blue-500 bg-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md motion-reduce:transform-none sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-muted-foreground">{t("voices.presetBadge")} · {voice.languageCode || "vi-VN"}</p>
          <h3 className="mt-4 text-2xl font-black tracking-[-0.045em] text-foreground">{voice.displayName}</h3>
          <p className="mt-2 text-sm leading-5 text-muted-foreground">{t("voices.presetDescription")}</p>
        </div>
        <span aria-hidden="true" className="pt-1 text-xl leading-none tracking-[0.2em] text-muted-foreground/70">•••</span>
      </div>

      <div className="mt-auto">
        <div className="mt-6 flex items-center gap-4">
             <VoicePreviewButton voiceId={voice.voiceType} label={voice.displayName} sampleText={sampleText} onPlayStart={onPlayStart} compact />
          <VoiceWaveform accent="coral" />
          <span className="ml-auto text-sm font-medium tabular-nums text-muted-foreground">{t("voices.previewDuration")}</span>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm font-medium text-muted-foreground">
          {metadata.map((item, index) => <span key={item} className={index > 0 ? "relative pl-3 before:absolute before:left-0 before:top-1/2 before:h-1 before:w-1 before:-translate-y-1/2 before:rounded-full before:bg-muted-foreground/50" : undefined}>{item}</span>)}
        </div>
        <div className="mt-4 flex items-center justify-between gap-4 border-t border-border pt-4">
          <Link
            href={`/?voice=${encodeURIComponent(voice.voiceType)}`}
            className="inline-flex items-center text-base font-black tracking-tight text-foreground transition-colors hover:text-[#df604e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            title={t("voices.useVoiceTitle")}
          >
            {t("voices.useVoice")} <span className="ml-2 text-[#df604e]">→</span>
          </Link>
          <span className="text-xs font-medium text-muted-foreground">{t("voices.previewHint")}</span>
        </div>
      </div>
    </article>
  )
}
