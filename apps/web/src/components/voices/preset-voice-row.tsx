import { Link } from "@tanstack/react-router"
import { Voice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { providerLabel } from "./voice-library-utils"
import { VoicePreviewButton } from "./voice-preview-button"
import { VoiceWaveform } from "./voice-waveform"
import { Sparkles, ArrowRight, Radio } from "lucide-react"

const styleLabels: Record<string, string> = {
  tu_nhien: "Tự nhiên",
  tin_tuc: "Tin tức",
  doc_truyen: "Đọc truyện",
}

function voiceProfileLine(voice: Voice) {
  const gender = voice.gender === "male" ? "Nam" : voice.gender === "female" ? "Nữ" : null
  const style = voice.style ? styleLabels[voice.style] || voice.style : null
  const parts = [gender, voice.region, style].filter(Boolean)
  return parts.length > 0 ? parts.join(" · ") : voice.description
}

export function PresetVoiceRow({ voice, onPlayStart }: { voice: Voice; onPlayStart?: (voiceId: string) => void }) {
  const { t } = useTranslation()
  const sampleText = t("voices.sampleSentence", { name: voice.displayName })
  const metadata = [providerLabel(voice.providerId), t("voices.presetMetaStyle"), t("voices.presetMetaPopularity")]

  return (
    <article className="group relative flex min-h-[220px] flex-col justify-between rounded-2xl border border-border/70 bg-card p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md motion-reduce:transform-none">
      {/* Top Section */}
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-primary">
                <Sparkles className="h-2.5 w-2.5" />
                {t("voices.presetBadge")}
              </span>
              <span className="inline-flex items-center rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-bold text-muted-foreground">
                {voice.languageCode || "vi-VN"}
              </span>
            </div>

            <h3 className="mt-2 text-2xl font-black tracking-tight text-foreground group-hover:text-primary transition-colors truncate">
              {voice.displayName}
            </h3>
          </div>

          {voiceProfileLine(voice) && (
            <span className="shrink-0 inline-flex items-center gap-1 rounded-lg border border-border/60 bg-muted/40 px-2 py-1 text-[11px] font-bold text-foreground/80">
              <Radio className="h-3 w-3 text-primary" />
              {voiceProfileLine(voice)}
            </span>
          )}
        </div>
      </div>

      {/* Audio Player Strip */}
      <div className="my-3 flex items-center gap-2.5 rounded-xl border border-border/50 bg-muted/20 px-2.5 py-2 transition-colors group-hover:bg-muted/40">
        <VoicePreviewButton
          voiceId={voice.voiceType}
          label={voice.displayName}
          sampleText={sampleText}
          onPlayStart={onPlayStart}
          compact
          size="sm"
        />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-2 overflow-hidden">
          <VoiceWaveform accent="coral" />
          <span className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
            {t("voices.previewDuration")}
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

        <Link
          to="/"
          search={{ voice: voice.voiceType }}
          className="shrink-0 inline-flex items-center gap-1 text-xs font-bold text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          title={t("voices.useVoiceTitle")}
        >
          <span>{t("voices.useVoice")}</span>
          <ArrowRight className="h-3.5 w-3.5 text-primary transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </article>
  )
}
