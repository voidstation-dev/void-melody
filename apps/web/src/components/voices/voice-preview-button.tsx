"use client"

import { Loader2, Pause, Play, RefreshCcw } from "lucide-react"
import { useVoicePreview } from "@/hooks/use-voice-preview"
import { useTranslation } from "@/hooks/use-translation"

type VoicePreviewButtonProps = {
  voiceId: string
  sampleText: string
  label?: string
  onPlayStart?: (voiceId: string) => void
  variant?: "preset" | "custom"
  compact?: boolean
  className?: string
}

export function VoicePreviewButton({ voiceId, sampleText, label: voiceLabel = voiceId, onPlayStart, variant = "preset", compact = false, className = "" }: VoicePreviewButtonProps) {
  const { t } = useTranslation()
  const preview = useVoicePreview(voiceId)
  const actionLabel = preview.isPlaying ? t("voices.playingBtn") : t("voices.previewBtn")
  const tone = compact
    ? preview.isPlaying
      ? "bg-emerald-500 text-white shadow-sm hover:bg-emerald-600"
      : variant === "custom"
        ? "bg-[#df604e] text-white shadow-sm hover:bg-[#c95242]"
        : "bg-foreground text-background shadow-sm hover:bg-foreground/90"
    : preview.isPlaying
      ? "bg-emerald-500 text-white shadow-sm hover:bg-emerald-600"
      : variant === "custom"
        ? "border border-border bg-muted/50 text-foreground hover:bg-muted"
        : "border border-border bg-card text-foreground hover:border-primary/40 hover:bg-muted/60"
  const buttonClassName = compact
    ? `inline-flex h-16 w-16 shrink-0 items-center justify-center rounded-full p-0 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60 ${tone}`
    : `inline-flex min-h-9 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60 ${tone}`

  return (
    <div className={`flex min-w-0 flex-col items-start gap-1 ${className}`}>
      <button
        type="button"
        onClick={() => { onPlayStart?.(voiceId); void preview.play(sampleText) }}
        disabled={preview.isLoading}
        className={buttonClassName}
        aria-label={`${actionLabel} ${voiceLabel}`}
        aria-pressed={preview.isPlaying}
      >
        {preview.isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : preview.isPlaying ? <Pause className="h-3.5 w-3.5 fill-current" /> : <Play className="h-3.5 w-3.5 fill-current" />}
        <span className={compact ? "sr-only" : undefined}>{preview.isLoading ? t("voices.loadingBtn") : actionLabel}</span>
      </button>
      {preview.error && (
        <div className="flex max-w-full items-center gap-1 text-[11px] font-semibold text-destructive" role="alert">
          <span className="truncate">{preview.error === "playback" ? t("voices.playbackError") : preview.error}</span>
          <button
            type="button"
            onClick={() => void preview.retry(sampleText)}
            className="inline-flex shrink-0 items-center gap-1 rounded-md px-1 py-0.5 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <RefreshCcw className="h-3 w-3" />
            {t("common.retry")}
          </button>
        </div>
      )}
    </div>
  )
}
