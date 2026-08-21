"use client"
import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Play, Pause, Loader2, Search, Trash2 } from "lucide-react"
import { PageContainer } from "@/components/app-shell/page-container"
import { VoiceCard } from "@/components/voices/voice-card"
import { useVoices } from "@/hooks/use-voices"
import { useCustomVoices } from "@/hooks/use-custom-voices"
import { apiFetch, apiFetchBlob } from "@/lib/api-client"
import { useTranslation } from "@/hooks/use-translation"

function CustomVoicePreviewButton({
  voice,
  activePlayingVoice,
  onPlayStart,
}: {
  voice: { id: string; transcript: string; display_name?: string }
  activePlayingVoice?: string | null
  onPlayStart?: (voiceId: string) => void
}) {
  const { t } = useTranslation();
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const isCurrentActive = activePlayingVoice ? activePlayingVoice === voice.id : isPlaying

  useEffect(() => {
    if (activePlayingVoice && activePlayingVoice !== voice.id && audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }, [activePlayingVoice, voice.id])

  useEffect(() => () => {
    if (audioUrl && typeof URL.revokeObjectURL === "function") {
      URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  const preview = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
      return
    }

    if (audioUrl && audioRef.current) {
      onPlayStart?.(voice.id)
      audioRef.current.currentTime = 0
      audioRef.current.play().catch(() => setIsPlaying(false))
      setIsPlaying(true)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const sampleText = voice.transcript || t("voices.sampleText", { name: voice.display_name || "" })
      const blob = await apiFetchBlob("/api/v1/tts/preview", {
        method: "POST",
        body: JSON.stringify({
          text: sampleText,
          voiceType: voice.id,
          rate: 1,
          style: "tu_nhien",
        }),
      })
      const url = URL.createObjectURL(blob)
      setAudioUrl(url)
      onPlayStart?.(voice.id)
      setIsPlaying(true)
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : t("errors.previewFailed"))
      setIsPlaying(false)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => void preview()}
          disabled={isLoading}
          className={`inline-flex items-center justify-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition-all ${
            isCurrentActive
              ? "bg-emerald-500 text-white shadow-sm hover:opacity-90"
              : "border border-border bg-muted/40 text-foreground hover:bg-muted hover:border-border/80"
          } disabled:opacity-40 active:scale-[0.98]`}
          aria-label={isCurrentActive ? `${t("voices.playingBtn")} ${voice.display_name}` : `${t("voices.previewBtn")} ${voice.display_name}`}
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
      </div>
      {error && <span className="text-[11px] font-semibold text-destructive" role="alert">{error}</span>}
    </div>
  )
}

export default function VoicesPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("")
  const [customPage, setCustomPage] = useState(1)
  const [tab, setTab] = useState<"all" | "preset" | "custom">("all")
  const [activePlayingVoice, setActivePlayingVoice] = useState<string | null>(null)

  const { data, isLoading } = useVoices(undefined, search)
  const customPageSize = 20
  const { data: customData, isLoading: customLoading } = useCustomVoices(search, customPage, customPageSize)
  const queryClient = useQueryClient()
  const deleteVoice = useMutation({
    mutationFn: (voiceId: string) => apiFetch<void>(`/api/v1/tts/voices/custom/${voiceId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["custom-voices"] }),
  })
  const showPreset = tab !== "custom"
  const showCustom = tab !== "preset"

  const presetCount = data?.items?.length ?? 0
  const customCount = customData?.total ?? 0

  return (
    <PageContainer>
      <div className="flex flex-col h-full">
        {/* Top Header */}
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between shrink-0">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t("voices.title")}</h1>
            <p className="text-sm text-muted-foreground mt-0.5">{t("voices.subtitle")}</p>
          </div>
          
          <div className="relative flex items-center max-w-xs w-full">
            <Search className="absolute left-3.5 h-4 w-4 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder={t("voices.searchPlaceholder")}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setCustomPage(1) }}
              className="w-full rounded-2xl border border-border bg-card pl-9 pr-4 py-2 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20 shadow-2xs font-medium"
            />
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex items-center gap-2 border-b border-border/80 pb-px">
          {(["all", "preset", "custom"] as const).map((value) => {
            const count = value === "all" ? presetCount + customCount : value === "preset" ? presetCount : customCount
            const isActive = tab === value
            return (
              <button
                key={value}
                type="button"
                onClick={() => setTab(value)}
                className={`relative px-4 py-2.5 text-xs font-bold transition-all flex items-center gap-2 ${
                  isActive 
                    ? "text-primary border-b-2 border-primary" 
                    : "text-muted-foreground hover:text-foreground border-b-2 border-transparent"
                }`}
              >
                <span>
                  {value === "all" ? t("voices.tabAll") : value === "preset" ? t("voices.tabPreset") : t("voices.tabCustom")}
                </span>
                <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                  isActive ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                }`}>
                  {count}
                </span>
              </button>
            )
          })}
        </div>

        {/* Content Section */}
        <div className="flex-1 overflow-y-auto min-h-0 pr-2 pb-8">
          {(isLoading && showPreset) || (customLoading && showCustom) ? (
            <div className="flex items-center justify-center min-h-[200px] text-sm text-muted-foreground gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span>{t("voices.loadingVoices")}</span>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Custom Cloned Voices */}
              {showCustom && (customData?.items.length ?? 0) > 0 && (
                <section>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-extrabold uppercase tracking-wider text-muted-foreground">
                        {t("voices.customHeading")}
                      </h2>
                      <span className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-bold text-violet-600 dark:text-violet-400">
                        VieNeu Clone
                      </span>
                    </div>

                    <Link 
                      href="/vieneu" 
                      className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
                    >
                      <span>+ {t("voices.newVoice")}</span>
                    </Link>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {customData?.items.map((voice) => (
                      <article 
                        key={voice.id} 
                        className="group relative flex flex-col justify-between rounded-2xl border border-border/80 bg-card p-5 shadow-xs transition-all duration-200 hover:border-primary/40 hover:shadow-md"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2">
                            <span className="rounded-full bg-violet-500/10 border border-violet-500/20 px-2.5 py-0.5 text-[11px] font-bold text-violet-600 dark:text-violet-400">
                              Custom · VieNeu
                            </span>
                            {voice.quality_score != null && (
                              <span className="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-bold text-muted-foreground">
                                {voice.quality_score}/100
                              </span>
                            )}
                          </div>

                          <h3 className="mt-3.5 text-base font-bold text-foreground group-hover:text-primary transition-colors">
                            {voice.display_name}
                          </h3>

                          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                            {(voice.reference_duration_seconds ?? voice.duration_seconds) != null
                              ? t("voices.referenceDuration", { duration: (voice.reference_duration_seconds ?? voice.duration_seconds ?? 0).toFixed(1) })
                              : t("voices.customDescription")}
                          </p>
                        </div>

                        <div className="mt-5 flex items-center gap-2 pt-4 border-t border-border/60">
                          <Link 
                            href={`/?voice=${encodeURIComponent(voice.id)}`} 
                            className="flex-1 inline-flex items-center justify-center rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground hover:opacity-90 transition-all shadow-2xs active:scale-[0.98]"
                          >
                            {t("voices.useVoice")}
                          </Link>

                          <CustomVoicePreviewButton
                            voice={voice}
                            activePlayingVoice={activePlayingVoice}
                            onPlayStart={(id) => setActivePlayingVoice(id)}
                          />

                          <button
                            type="button"
                            onClick={() => {
                              if (confirm(t("voices.confirmDelete"))) {
                                deleteVoice.mutate(voice.id);
                              }
                            }}
                            disabled={deleteVoice.isPending}
                            className="inline-flex items-center justify-center rounded-xl border border-border bg-muted/30 p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-all active:scale-[0.98]"
                            title={t("voices.deleteVoice")}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>

                  {customData && customData.total > customPageSize && (
                    <div className="mt-4 flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">
                        {t("voices.pageInfo", { current: customPage, total: Math.ceil(customData.total / customPageSize) })}
                      </span>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={customPage === 1}
                          onClick={() => setCustomPage((page) => page - 1)}
                          className="rounded-xl border border-border px-3.5 py-1.5 font-bold disabled:opacity-40 hover:bg-muted transition-colors"
                        >
                          {t("common.previous")}
                        </button>
                        <button
                          type="button"
                          disabled={customPage >= Math.ceil(customData.total / customPageSize)}
                          onClick={() => setCustomPage((page) => page + 1)}
                          className="rounded-xl border border-border px-3.5 py-1.5 font-bold disabled:opacity-40 hover:bg-muted transition-colors"
                        >
                          {t("common.next")}
                        </button>
                      </div>
                    </div>
                  )}
                </section>
              )}

              {/* Preset Voices */}
              {showPreset && (
                <section>
                  <div className="flex items-center gap-2 mb-4">
                    <h2 className="text-sm font-extrabold uppercase tracking-wider text-muted-foreground">
                      {t("voices.presetHeading")}
                    </h2>
                    <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                      Standard
                    </span>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {data?.items.map((voice) => (
                      <VoiceCard
                        key={voice.voiceType}
                        voice={voice}
                        activePlayingVoice={activePlayingVoice}
                        onPlayStart={(vt) => setActivePlayingVoice(vt)}
                      />
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
