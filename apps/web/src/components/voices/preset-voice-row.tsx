import { Link } from "@tanstack/react-router"
import { Voice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { providerLabel } from "./voice-library-utils"
import { VoicePreviewButton } from "./voice-preview-button"
import { VoiceWaveform } from "./voice-waveform"
import { ArrowRight } from "lucide-react"

function voiceProfileLine(voice: Voice, t: (key: any, params?: any) => string) {
  const gender = voice.gender === "male" ? t("voices.genderMale") : voice.gender === "female" ? t("voices.genderFemale") : null
  const style = voice.style === "tu_nhien" ? t("voices.styleNatural") : voice.style === "tin_tuc" ? t("voices.styleNews") : voice.style === "doc_truyen" ? t("voices.styleStory") : voice.style
  const parts = [gender, voice.region, style].filter(Boolean)
  return parts.length > 0 ? parts.join(" · ") : null
}

export function PresetVoiceRow({ voice, onPlayStart }: { voice: Voice; onPlayStart?: (voiceId: string) => void }) {
  const { t } = useTranslation()
  const sampleText = t("voices.sampleSentence", { name: voice.displayName })
  const profile = voiceProfileLine(voice, t)

  return (
    <article className="group relative flex flex-col justify-between rounded-xl border border-border/70 bg-card p-3 sm:p-3.5 shadow-2xs transition-all duration-200 hover:border-primary/50 hover:shadow-xs">
      {/* Header: Title + Meta & Use Voice Button */}
      <div className="flex items-start justify-between gap-2.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="inline-flex items-center gap-0.5 rounded-md bg-primary/10 px-1.5 py-0.2 text-[9px] font-extrabold uppercase tracking-wide text-primary">
              {t("voices.presetBadge")}
            </span>
            <span className="inline-flex items-center rounded-md bg-muted px-1.5 py-0.2 text-[9px] font-mono font-semibold text-muted-foreground">
              {voice.languageCode || "vi-VN"}
            </span>
            <h3 className="text-sm font-bold text-foreground group-hover:text-primary transition-colors truncate">
              {voice.displayName}
            </h3>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5 truncate">
            <span>{providerLabel(voice.providerId)}</span>
            {profile && (
              <>
                <span className="text-muted-foreground/40">•</span>
                <span>{profile}</span>
              </>
            )}
          </div>
        </div>

        <Link
          to="/"
          search={{ voice: voice.voiceType }}
          className="shrink-0 inline-flex items-center gap-1 rounded-lg bg-primary/10 hover:bg-primary text-primary hover:text-primary-foreground px-2.5 py-1 text-[11px] font-bold transition-all shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-95"
          title={t("voices.useVoiceTitle")}
        >
          <span>{t("voices.useVoice")}</span>
          <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>

      {/* Slim Audio Waveform Strip */}
      <div className="mt-2.5 flex items-center gap-2 rounded-lg border border-border/50 bg-muted/25 px-2 py-1.5 transition-colors group-hover:bg-muted/40">
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
          <span className="shrink-0 text-[10px] font-mono font-medium tabular-nums text-muted-foreground">
            {t("voices.previewDuration")}
          </span>
        </div>
      </div>
    </article>
  )
}
