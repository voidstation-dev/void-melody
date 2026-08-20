"use client"

import { ChangeEvent, DragEvent, useRef, useState } from "react"
import { AudioLines, Check, FileAudio, Mic2, ShieldCheck, Sparkles, Upload, UserRoundPlus } from "lucide-react"
import { useVoiceCapabilities } from "@/hooks/use-voice-capabilities"
import { useVoiceLab } from "@/hooks/use-voice-lab"
import { useTTSJob } from "@/hooks/use-tts-job"
import { apiFetch } from "@/lib/api-client"
import { BatchJobCreateResponse } from "@/types/tts-job"

type Section = "voices" | "cloning"

const ACCEPTED_AUDIO = ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a"]
const ACCEPTED_EXTENSIONS = [".wav", ".mp3", ".m4a"]
const MAX_FILE_BYTES = 50 * 1024 * 1024

function formatBytes(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function RuntimeBadge({ isLoading, available, reason }: { isLoading: boolean; available: boolean; reason?: string | null }) {
  if (isLoading) return <span className="rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground">Checking runtime…</span>
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${available ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}`} title={reason ?? undefined}><span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${available ? "bg-emerald-500" : "bg-amber-500"}`} />{available ? "Clone ready" : "Clone unavailable"}</span>
}

function StepCard({ step, title, children }: { step: string; title: string; children: React.ReactNode }) {
  return <section className="rounded-2xl border border-border bg-card p-5 shadow-sm"><div className="mb-4 flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">{step}</span><h2 className="text-base font-bold">{title}</h2></div>{children}</section>
}

function Waveform({ peaks = [] }: { peaks?: number[] }) {
  const bars = peaks.length ? peaks : [24, 42, 30, 64, 48, 78, 54, 36, 70, 46, 82, 58, 32, 66, 44, 74, 40, 60, 28, 52, 38, 72, 48, 34, 68, 44, 76, 56, 32, 62, 42, 70]
  return <div className="flex h-24 items-center gap-1 rounded-xl border border-dashed border-border bg-muted/40 p-3" aria-label="Audio waveform preview">{bars.map((height, index) => <span key={index} className="w-full rounded-full bg-muted-foreground/25" style={{ height: `${height}%` }} />)}</div>
}

export function VieneuPage() {
  const [section, setSection] = useState<Section>("voices")
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [voiceName, setVoiceName] = useState("")
  const [consent, setConsent] = useState(false)
  const [previewText, setPreviewText] = useState("")
  const [previewRate, setPreviewRate] = useState("1")
  const [previewJobId, setPreviewJobId] = useState<string | null>(null)
  const [selectedSegment, setSelectedSegment] = useState<{ start: number; end: number } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const capabilities = useVoiceCapabilities()
  const { analysis: analysisMutation, clone: cloneMutation } = useVoiceLab()
  const runtime = capabilities.data
  const analysis = analysisMutation.data
  const profile = cloneMutation.data
  const { data: previewJob } = useTTSJob(previewJobId)
  const cloneAvailable = runtime?.supports_voice_cloning === true
  const selectedStart = selectedSegment?.start ?? analysis?.selected_start_seconds ?? 0
  const selectedEnd = selectedSegment?.end ?? analysis?.selected_end_seconds ?? 0
  const cloneAnalysis = analysis && {
    ...analysis,
    selected_start_seconds: selectedStart,
    selected_end_seconds: selectedEnd,
  }

  const selectFile = (nextFile: File | undefined) => {
    if (!nextFile) return
    const extension = `.${nextFile.name.split(".").pop()?.toLowerCase()}`
    if (!ACCEPTED_EXTENSIONS.includes(extension) || (nextFile.type && !ACCEPTED_AUDIO.includes(nextFile.type))) {
      setFile(null)
      setFileError("Choose a WAV, MP3, or M4A audio file.")
      return
    }
    if (nextFile.size > MAX_FILE_BYTES) {
      setFile(null)
      setFileError("Audio files must be smaller than 50 MB.")
      return
    }
    setFileError(null)
    setFile(nextFile)
    setSelectedSegment(null)
    analysisMutation.reset()
    cloneMutation.reset()
    analysisMutation.mutate(nextFile)
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    selectFile(event.dataTransfer.files[0])
  }

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0])

  const generatePreview = async () => {
    if (!profile || !previewText.trim()) return
    const response = await apiFetch<BatchJobCreateResponse>("/api/v1/tts/jobs", {
      method: "POST",
      body: JSON.stringify({
        text: previewText,
        voiceType: profile.id,
        rate: Number(previewRate),
        providerId: profile.provider_id,
      }),
    })
    setPreviewJobId(response.jobs[0]?.id ?? null)
  }

  return <div className="flex h-full min-h-0 flex-col">
    <header className="mb-5 flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><p className="mb-1 text-[11px] font-bold uppercase tracking-[0.18em] text-primary/60">VieNeu / local audio</p><h1 className="text-2xl font-bold tracking-tight">Voice Lab</h1><p className="mt-1 max-w-xl text-sm text-muted-foreground">Create reusable voice profiles from a short reference sample. Your audio stays on this device.</p></div><RuntimeBadge isLoading={capabilities.isLoading} available={cloneAvailable} reason={runtime?.reason} /></header>
    <div className="mb-5 flex shrink-0 items-center justify-between gap-4"><div className="inline-flex rounded-xl border border-border bg-card p-1 shadow-sm" role="tablist" aria-label="Voice Lab sections"><button type="button" role="tab" aria-selected={section === "voices"} onClick={() => setSection("voices")} className={`rounded-lg px-4 py-2 text-sm font-bold transition-colors ${section === "voices" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>Preset Voices</button><button type="button" role="tab" aria-selected={section === "cloning"} onClick={() => setSection("cloning")} className={`rounded-lg px-4 py-2 text-sm font-bold transition-colors ${section === "cloning" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>Clone Voice</button></div><span className="hidden text-xs text-muted-foreground sm:block">V3 Turbo · 48 kHz</span></div>
    {section === "voices" ? <div className="flex min-h-0 flex-1 items-center justify-center rounded-2xl border border-dashed border-border bg-card p-10 text-center shadow-sm"><div className="max-w-md"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary"><Mic2 className="h-7 w-7" /></div><h2 className="mt-5 text-lg font-bold">Preset Voices</h2><p className="mt-2 text-sm text-muted-foreground">Browse the built-in Vietnamese voices in Voice Library, or create a reusable profile from your own sample.</p><a href="/voices" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground transition-opacity hover:opacity-90"><AudioLines className="h-4 w-4" /> Open Voice Library</a></div></div> : <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6"><div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]"><div className="space-y-5">
      <StepCard step="1" title="Upload Sample"><div onDragOver={(event) => event.preventDefault()} onDrop={onDrop} className={`rounded-xl border border-dashed p-5 text-center transition-colors ${file ? "border-primary/40 bg-primary/[0.03]" : "border-border bg-muted/30 hover:border-primary/50"}`}><input ref={fileInputRef} id="voice-sample-file" aria-label="Voice sample file" type="file" accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4" onChange={onFileChange} className="sr-only" />{file ? <div className="flex items-center justify-between gap-3 text-left"><div className="flex min-w-0 items-center gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><FileAudio className="h-5 w-5" /></div><div className="min-w-0"><p className="truncate text-sm font-bold">{file.name}</p><p className="text-xs text-muted-foreground">{formatBytes(file.size)} · Local only</p></div></div><button type="button" onClick={() => { setFile(null); setFileError(null) }} className="shrink-0 text-xs font-semibold text-muted-foreground underline underline-offset-2 hover:text-foreground">Replace</button></div> : <><Upload className="mx-auto h-6 w-6 text-primary/70" /><p className="mt-3 text-sm font-semibold">Drop an audio sample here</p><p className="mt-1 text-xs text-muted-foreground">WAV, MP3, or M4A · up to 50 MB · 3–30 seconds</p><button type="button" onClick={() => fileInputRef.current?.click()} className="mt-4 rounded-lg border border-border bg-card px-4 py-2 text-xs font-bold shadow-sm hover:bg-muted">Choose File</button></>}</div>{fileError && <p className="mt-3 text-xs font-semibold text-destructive" role="alert">{fileError}</p>}<div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Audio is processed locally and never uploaded.</div></StepCard>
      <StepCard step="2" title="Auto Analysis">{file ? <><div className="mb-3 flex flex-wrap gap-2 text-xs"><span className={`rounded-full px-2.5 py-1 font-semibold ${analysisMutation.isError ? "bg-red-50 text-red-700" : analysisMutation.isPending ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>{analysisMutation.isError ? "Analysis failed" : analysisMutation.isPending ? "Analyzing…" : analysis ? "Analysis ready" : "Analysis pending"}</span><span className="rounded-full bg-muted px-2.5 py-1 font-semibold text-muted-foreground">Selected segment: {analysis ? `${selectedStart.toFixed(1)}–${selectedEnd.toFixed(1)}s` : "—"}</span></div><Waveform peaks={analysis?.waveform_peaks} />{analysis && <div className="mt-4 rounded-xl border border-border bg-muted/20 p-3"><div className="flex items-center justify-between text-xs"><span className="font-semibold">Reference segment</span><span className="font-bold text-primary">{selectedEnd - selectedStart > 0 ? `${(selectedEnd - selectedStart).toFixed(1)}s` : "—"} · max 8s</span></div><label className="mt-3 block text-xs text-muted-foreground">Start: {selectedStart.toFixed(1)}s<input aria-label="Reference segment start" type="range" min="0" max={Math.max(0, Math.min(selectedEnd - 1, analysis.duration_seconds - 1))} step="0.1" value={selectedStart} onChange={(event) => setSelectedSegment({ start: Math.min(Number(event.target.value), selectedEnd - 1), end: selectedEnd })} className="mt-2 w-full accent-primary" /></label><label className="mt-3 block text-xs text-muted-foreground">End: {selectedEnd.toFixed(1)}s<input aria-label="Reference segment end" type="range" min={Math.min(analysis.duration_seconds, selectedStart + 1)} max={Math.min(analysis.duration_seconds, selectedStart + 8)} step="0.1" value={selectedEnd} onChange={(event) => setSelectedSegment({ start: selectedStart, end: Number(event.target.value) })} className="mt-2 w-full accent-primary" /></label></div>}<div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">{[["Speech", analysis ? `${Math.round(analysis.speech_ratio * 100)}%` : "Waiting"], ["Noise", analysis ? `${analysis.noise_level_db} dB` : "Waiting"], ["Clipping", analysis ? `${(analysis.clipping_ratio * 100).toFixed(1)}%` : "Waiting"], ["Quality", analysis ? `${analysis.quality_score}/100` : "Not set"]].map(([label, value]) => <div key={label}><p className="text-muted-foreground">{label}</p><p className="mt-1 font-bold">{value}</p></div>)}</div>{analysis?.warnings.map((warning) => <p key={warning} className="mt-3 text-xs font-semibold text-amber-700">{warning}</p>)}</> : <div className="flex min-h-24 items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 text-center text-sm text-muted-foreground">Upload a sample to see its waveform and recommended reference segment.</div>}</StepCard>
      <StepCard step="3" title="Create Voice Profile"><div className="grid gap-4 sm:grid-cols-2"><label className="text-xs font-semibold">Voice Name<input value={voiceName} onChange={(event) => setVoiceName(event.target.value)} placeholder="e.g. My narration voice" className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none ring-primary/20 focus:ring-4" /></label><label className="text-xs font-semibold">Language<input value="Vietnamese" readOnly className="mt-2 w-full rounded-lg border border-border bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground outline-none" /></label></div><div className="mt-4 flex items-center justify-between rounded-xl border border-border bg-muted/30 p-3 text-xs"><span className="font-semibold">Engine</span><span className="font-bold">VieNeu v3 Turbo · {runtime?.backend ?? "—"}</span></div><label className="mt-4 flex items-start gap-3 text-xs leading-5 text-muted-foreground"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-1 h-4 w-4 accent-primary" /><span>I confirm I own this voice or have permission to use it. Do not use cloned voices to impersonate people deceptively.</span></label><button type="button" onClick={() => file && cloneAnalysis && cloneMutation.mutate({ file, displayName: voiceName, consentGiven: consent, analysis: cloneAnalysis })} disabled={!cloneAvailable || !file || !cloneAnalysis || !voiceName.trim() || !consent || cloneMutation.isPending} className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-foreground transition-opacity disabled:cursor-not-allowed disabled:opacity-40"><UserRoundPlus className="h-4 w-4" /> {cloneMutation.isPending ? "Creating…" : "Create Voice"}</button>{!cloneAvailable && <p className="mt-3 text-xs font-semibold text-amber-700">{runtime?.reason ?? "Checking whether this device can clone voices."}</p>}{cloneMutation.isError && <p className="mt-3 text-xs font-semibold text-destructive" role="alert">Voice profile could not be created. Check the sample and try again.</p>}</StepCard>
    </div><aside className="h-fit rounded-2xl border border-border bg-card p-5 shadow-sm xl:sticky xl:top-0"><div className="flex items-center justify-between"><h2 className="text-base font-bold">Preview &amp; Output</h2><Sparkles className="h-4 w-4 text-primary/60" /></div><div className="mt-5 space-y-4 text-sm"><div className="flex items-center justify-between border-b border-border pb-3"><span className="text-muted-foreground">Reference</span><span className="font-semibold">{file ? "Selected sample" : "Not selected"}</span></div><div className="flex items-center justify-between border-b border-border pb-3"><span className="text-muted-foreground">Analysis</span><span className="font-semibold">{analysis ? "Ready" : file ? "Pending" : "Waiting"}</span></div><div className="flex items-center justify-between border-b border-border pb-3"><span className="text-muted-foreground">Engine</span><span className="font-semibold">VieNeu v3 Turbo</span></div><div className="rounded-xl bg-muted/50 p-4"><p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Profile status</p><p className="mt-2 text-sm font-bold">{profile?.display_name ?? "No profile yet"}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{profile ? "Ready to reuse in Voice Library and Melody jobs." : "Create a profile to unlock preview generation and reuse across Melody jobs."}</p></div>{previewJob && <div className="rounded-xl border border-border p-4"><p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Preview</p><p className="mt-2 text-sm font-semibold">{previewJob.status === "completed" ? "Preview ready" : `Preview ${previewJob.status}`}</p>{previewJob.audioUrl && <audio className="mt-3 w-full" controls src={previewJob.audioUrl} />}</div>}</div></aside></div><section className="mt-5 rounded-2xl border border-border bg-card p-5 shadow-sm"><div className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /><h2 className="text-base font-bold">Generate with this Voice</h2></div><div className="mt-4 grid gap-4 lg:grid-cols-[1fr_180px_auto] lg:items-end"><label className="text-xs font-semibold">Preview text<textarea value={previewText} onChange={(event) => setPreviewText(event.target.value)} disabled={!profile} placeholder={profile ? "Type a short preview…" : "Create a voice profile first"} className="mt-2 min-h-20 w-full resize-y rounded-lg border border-border bg-muted/40 px-3 py-2.5 text-sm outline-none" /></label><label className="text-xs font-semibold">Speed<select value={previewRate} onChange={(event) => setPreviewRate(event.target.value)} disabled={!profile} className="mt-2 w-full rounded-lg border border-border bg-muted/40 px-3 py-2.5 text-sm"><option value="0.5">0.5×</option><option value="1">1.0×</option><option value="2">2.0×</option></select></label><button type="button" onClick={() => void generatePreview()} disabled={!profile || !previewText.trim() || previewJob?.status === "queued" || previewJob?.status === "processing"} className="rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-foreground disabled:opacity-40">Generate Preview</button></div></section></div>}</div>
}
