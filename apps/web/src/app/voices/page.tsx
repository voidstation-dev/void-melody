"use client"
import { useEffect, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { PageContainer } from "@/components/app-shell/page-container"
import { VoiceCard } from "@/components/voices/voice-card"
import { useVoices } from "@/hooks/use-voices"
import { useCustomVoices } from "@/hooks/use-custom-voices"
import { apiFetch, apiFetchBlob } from "@/lib/api-client"

function VoicePreviewButton({ voice }: { voice: { id: string; transcript: string } }) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
  }, [audioUrl])

  const preview = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const blob = await apiFetchBlob("/api/v1/tts/preview", {
        method: "POST",
        body: JSON.stringify({
          text: voice.transcript || "Xin chào, đây là bản xem trước của giọng đọc.",
          voiceType: voice.id,
          rate: 1,
          style: "tu_nhien",
        }),
      })
      setAudioUrl(URL.createObjectURL(blob))
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Preview failed")
    } finally {
      setIsLoading(false)
    }
  }

  return <div className="flex items-center gap-2"><button type="button" onClick={() => void preview()} disabled={isLoading} className="rounded-lg border border-border px-3 py-2 text-xs font-bold text-muted-foreground disabled:opacity-40">{isLoading ? "Loading…" : "Preview"}</button>{audioUrl && <audio className="h-8 max-w-40" controls autoPlay src={audioUrl} />}{error && <span className="text-xs text-destructive" role="alert">{error}</span>}</div>
}

export default function VoicesPage() {
  const [search, setSearch] = useState("")
  const [customPage, setCustomPage] = useState(1)
  const [tab, setTab] = useState<"all" | "preset" | "custom">("all")
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

  return (
    <PageContainer>
      <div className="flex flex-col h-full">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between shrink-0">
          <div>
            <h1 className="text-2xl font-bold">Voice Library</h1>
            <p className="text-sm text-muted-foreground">Preset voices and reusable local profiles</p>
          </div>
          <input
            type="text"
            placeholder="Tìm giọng đọc..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCustomPage(1) }}
            className="rounded-lg border border-border bg-card px-4 py-2 text-sm focus:outline-none"
          />
        </div>

        <div className="mb-5 flex gap-2 border-b border-border">
          {(["all", "preset", "custom"] as const).map((value) => <button key={value} type="button" onClick={() => setTab(value)} className={`border-b-2 px-3 py-2 text-xs font-bold capitalize ${tab === value ? "border-primary text-foreground" : "border-transparent text-muted-foreground"}`}>{value === "custom" ? "My Voices" : value}</button>)}
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 pr-2 pb-6">
          {(isLoading && showPreset) || (customLoading && showCustom) ? (
            <div className="text-sm text-muted-foreground">Loading voices...</div>
          ) : (
            <div className="space-y-8">
              {showCustom && (customData?.items.length ?? 0) > 0 && <section><h2 className="mb-3 text-sm font-bold">My Voices</h2><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{customData?.items.map((voice) => <article key={voice.id} className="rounded-xl border border-primary/20 bg-card p-5 shadow-sm"><div className="flex items-center justify-between"><span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">Custom · VieNeu</span><span className="text-xs text-muted-foreground">{voice.quality_score != null ? `${voice.quality_score}/100` : "—"}</span></div><h3 className="mt-3 text-base font-bold">{voice.display_name}</h3><p className="mt-1 text-xs text-muted-foreground">{(voice.reference_duration_seconds ?? voice.duration_seconds) != null ? `${(voice.reference_duration_seconds ?? voice.duration_seconds ?? 0).toFixed(1)}s reference` : "Reference profile"}</p><div className="mt-4 flex flex-wrap gap-2"><a href={`/vieneu?voice=${voice.id}`} className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground">Use</a><VoicePreviewButton voice={voice} /><button type="button" onClick={() => deleteVoice.mutate(voice.id)} disabled={deleteVoice.isPending} className="rounded-lg border border-border px-3 py-2 text-xs font-bold text-muted-foreground">Delete</button></div></article>)}</div>{customData && customData.total > customPageSize && <div className="mt-4 flex items-center justify-between text-xs"><span className="text-muted-foreground">Page {customPage} of {Math.ceil(customData.total / customPageSize)}</span><div className="flex gap-2"><button type="button" disabled={customPage === 1} onClick={() => setCustomPage((page) => page - 1)} className="rounded-lg border border-border px-3 py-1.5 font-semibold disabled:opacity-40">Previous</button><button type="button" disabled={customPage >= Math.ceil(customData.total / customPageSize)} onClick={() => setCustomPage((page) => page + 1)} className="rounded-lg border border-border px-3 py-1.5 font-semibold disabled:opacity-40">Next</button></div></div>}</section>}
              {showPreset && <section><h2 className="mb-3 text-sm font-bold">Preset Voices</h2><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{data?.items.map((voice) => <VoiceCard key={voice.voiceType} voice={voice} />)}</div></section>}
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
