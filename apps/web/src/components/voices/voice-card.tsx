"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { Play, Pause, Loader2 } from "lucide-react"
import { Voice } from "@/types/voice"
import { apiFetchBlob } from "@/lib/api-client"
import { useTranslation } from "@/hooks/use-translation"

interface VoiceCardProps {
  voice: Voice
  activePlayingVoice?: string | null
  onPlayStart?: (voiceType: string) => void
}

export function VoiceCard({ voice, activePlayingVoice, onPlayStart }: VoiceCardProps) {
  const { t } = useTranslation();
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const isCurrentActive = activePlayingVoice ? activePlayingVoice === voice.voiceType : isPlaying

  // Stop playback if another card starts playing
  useEffect(() => {
    if (activePlayingVoice && activePlayingVoice !== voice.voiceType && audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }, [activePlayingVoice, voice.voiceType])

  useEffect(() => {
    return () => {
      if (audioUrl && typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [audioUrl])

  const sampleText = t("voices.sampleSentence", { name: voice.displayName })

  const handleTogglePreview = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
      return
    }

    if (audioUrl && audioRef.current) {
      onPlayStart?.(voice.voiceType)
      audioRef.current.currentTime = 0
      audioRef.current.play().catch(() => setIsPlaying(false))
      setIsPlaying(true)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const blob = await apiFetchBlob("/api/v1/tts/preview", {
        method: "POST",
        body: JSON.stringify({
          text: sampleText,
          voiceType: voice.voiceType,
          rate: 1.0,
          style: "tu_nhien",
        }),
      })
      const url = URL.createObjectURL(blob)
      setAudioUrl(url)
      onPlayStart?.(voice.voiceType)
      setIsPlaying(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.previewFailed"))
      setIsPlaying(false)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      className={`group relative flex flex-col justify-between rounded-2xl border p-5 shadow-xs transition-all duration-200 ${
        isCurrentActive
          ? "border-primary bg-primary/[0.03] ring-2 ring-primary/20 shadow-md"
          : "border-border bg-card hover:border-primary/40 hover:shadow-md"
      }`}
    >
      <div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
              {voice.languageCode || "vi-VN"}
            </span>
            <span className="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              {t("voices.presetBadge")}
            </span>
          </div>

          {isCurrentActive && (
            <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
              </span>
              {t("voices.playingBadge")}
            </span>
          )}
        </div>

        <h3 className="mt-3.5 text-base font-bold text-foreground group-hover:text-primary transition-colors flex items-center gap-1.5">
          <span>{voice.displayName}</span>
        </h3>
        
        <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
          {t("voices.presetDescription")}
        </p>
      </div>

      <div className="mt-5 pt-4 border-t border-border/60">
        <div className="flex items-center gap-2">
          <Link
            href={`/?voice=${encodeURIComponent(voice.voiceType)}`}
            className="flex-1 inline-flex items-center justify-center gap-1 rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground hover:opacity-90 transition-all shadow-2xs active:scale-[0.98]"
            title={t("voices.useVoiceTitle")}
          >
            <span>{t("voices.useVoice")}</span>
          </Link>

          <button
            type="button"
            onClick={handleTogglePreview}
            disabled={isLoading}
            className={`inline-flex items-center justify-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition-all ${
              isCurrentActive
                ? "bg-emerald-500 text-white shadow-sm hover:opacity-90"
                : "border border-border bg-muted/40 text-foreground hover:bg-muted hover:border-border/80"
            } disabled:opacity-50 active:scale-[0.98]`}
            aria-label={isCurrentActive ? `${t("voices.playingBtn")} ${voice.displayName}` : `${t("voices.previewBtn")} ${voice.displayName}`}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{t("voices.loadingBtn")}</span>
              </>
            ) : isCurrentActive ? (
              <>
                <Pause className="h-3.5 w-3.5 fill-current" />
                <span>{t("voices.playingBtn")}</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current ml-0.5" />
                <span>{t("voices.previewBtn")}</span>
              </>
            )}
          </button>
        </div>

        {audioUrl && (
          <audio
            ref={audioRef}
            src={audioUrl}
            autoPlay={isPlaying}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            onError={() => {
              setIsPlaying(false)
              setError(t("voices.playbackError"))
            }}
            className="hidden"
          />
        )}

        {error && (
          <p className="mt-2 text-[11px] font-semibold text-destructive" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
