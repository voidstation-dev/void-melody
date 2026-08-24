
import { useEffect, useMemo, useRef, useState } from "react"
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronDown,
  CircleAlert,
  Download,
  FileUp,
  Loader2,
  Pause,
  RotateCcw,
  Sparkles,
  UploadCloud,
} from "lucide-react"
import { useCustomVoices } from "@/hooks/use-custom-voices"
import { useVoices } from "@/hooks/use-voices"
import { apiFetch, apiFetchBlob } from "@/lib/api-client"
import type { Voice } from "@/types/voice"
import type { RenderSegment, ScriptDocument, ScriptParseResponse, ScriptRender } from "@/types/emotional-script"
import { countDeliveryTags } from "./emotional-script-utils"

const tagOptions = [
  { label: "Cười", value: "[cười]", kind: "native" },
  { label: "Thở dài", value: "[thở dài]", kind: "native" },
  { label: "Hắng giọng", value: "[hắng giọng]", kind: "native" },
  { label: "Bình tĩnh", value: "[bình tĩnh]", kind: "approx" },
  { label: "Vui", value: "[vui]", kind: "approx" },
  { label: "Buồn", value: "[buồn]", kind: "approx" },
  { label: "Sợ hãi", value: "[sợ hãi]", kind: "approx" },
  { label: "Tức giận", value: "[tức giận]", kind: "approx" },
  { label: "Bất ngờ", value: "[bất ngờ]", kind: "approx" },
  { label: "Căng thẳng", value: "[căng thẳng]", kind: "approx" },
  { label: "Bí ẩn", value: "[bí ẩn]", kind: "approx" },
  { label: "Kể chuyện", value: "[kể chuyện]", kind: "approx" },
  { label: "Gầm lên", value: "[gầm lên]", kind: "approx" },
  { label: "Thì thầm", value: "[thì thầm]", kind: "unsupported" },
] as const

const terminalStatuses = new Set(["completed", "partial_failed", "failed", "cancelled", "interrupted"])

function voiceLabel(voice: Voice) {
  return `${voice.displayName} · Preset`
}

function segmentLabel(segment: RenderSegment) {
  if (segment.status === "ready" || segment.status === "reused") return "Đã tạo"
  if (segment.status === "rendering") return "Đang tạo"
  if (segment.status === "failed") return "Lỗi"
  return "Chưa tạo"
}

export function EmotionalScriptPage() {
  const [text, setText] = useState("")
  const [globalPrompt, setGlobalPrompt] = useState("")
  const [selectedVoice, setSelectedVoice] = useState("")
  const [outputFormat, setOutputFormat] = useState<"mp3" | "wav">("mp3")
  const [document, setDocument] = useState<ScriptDocument | null>(null)
  const [render, setRender] = useState<ScriptRender | null>(null)
  const [audioBlobUrl, setAudioBlobUrl] = useState<string | null>(null)
  const [audioLoadError, setAudioLoadError] = useState<string | null>(null)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [isBusy, setIsBusy] = useState(false)
  const [notice, setNotice] = useState<{ tone: "info" | "error" | "success"; text: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { data: presetVoices } = useVoices("vi-VN", undefined, "vieneu")
  const { data: customVoices } = useCustomVoices(undefined, 1, 100)

  const voices = useMemo(() => {
    const presets = (presetVoices?.items ?? []).filter((voice) => voice.providerId === "vieneu" || !voice.providerId)
    const clones: Voice[] = (customVoices?.items ?? []).map((voice) => ({
      id: voice.id,
      voiceType: voice.id,
      displayName: voice.display_name,
      languageCode: "vi-VN",
      languageShort: "vi",
      resourceId: "",
      capturedAt: null,
      providerId: "vieneu",
    }))
    return [...presets, ...clones]
  }, [customVoices?.items, presetVoices?.items])

  useEffect(() => {
    if (!render || terminalStatuses.has(render.status)) return
    const timer = window.setInterval(async () => {
      try {
        const latest = await apiFetch<ScriptRender>(`/api/v1/script-renders/${render.id}`)
        setRender(latest)
      } catch {
        // Polling is best-effort; the action card remains usable for retry.
      }
    }, 1200)
    return () => window.clearInterval(timer)
  }, [render])

  useEffect(() => {
    if (!render || render.status !== "completed" || !render.output_url) {
      return
    }

    let disposed = false
    let objectUrl: string | null = null

    void apiFetchBlob(render.output_url)
      .then((blob) => {
        if (disposed) return
        objectUrl = URL.createObjectURL(blob)
        setAudioBlobUrl(objectUrl)
      })
      .catch((error) => {
        if (disposed) return
        setAudioLoadError(error instanceof Error ? error.message : "Không thể tải audio.")
      })

    return () => {
      disposed = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      setAudioBlobUrl(null)
      setAudioLoadError(null)
    }
  }, [render])

  const tagCounts = countDeliveryTags(text)
  const activeVoiceId = selectedVoice || voices[0]?.voiceType || ""
  const lineCount = document?.scenes.reduce((sum, scene) => sum + scene.lines.length, 0) ?? (text.trim() ? 1 : 0)
  const speakerCount = document?.speakers.length ?? 0
  const selectedVoiceObject = voices.find((voice) => voice.voiceType === activeVoiceId)
  const isClone = Boolean(selectedVoiceObject && customVoices?.items.some((voice) => voice.id === selectedVoiceObject.voiceType))

  const parseCurrentText = async (content: string, fileName?: string) => {
    const parsed = await apiFetch<ScriptParseResponse>("/api/v1/scripts/parse", {
      method: "POST",
      body: JSON.stringify({ content, format: "auto", original_name: fileName ?? null }),
    })
    const nextDocument: ScriptDocument = {
      ...parsed.document,
      defaults: {
        ...parsed.document.defaults,
        voice_id: activeVoiceId || null,
        global_delivery_prompt: globalPrompt || null,
      },
    }
    setDocument(nextDocument)
    return nextDocument
  }

  const handleImport = async (file: File) => {
    setIsBusy(true)
    setNotice(null)
    try {
      const content = await file.text()
      setText(content)
      await parseCurrentText(content, file.name)
      setReviewOpen(true)
      setNotice({ tone: "success", text: "Parse thành công. Kiểm tra mapping trước khi tạo audio." })
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Không thể đọc file kịch bản." })
    } finally {
      setIsBusy(false)
    }
  }

  const assignSpeaker = (speakerId: string, voiceId: string) => {
    setDocument((current) => current ? {
      ...current,
      speakers: current.speakers.map((speaker) => speaker.id === speakerId ? { ...speaker, voice_id: voiceId } : speaker),
    } : current)
  }

  const handleGenerate = async () => {
    if (!text.trim() || !activeVoiceId || isBusy) return
    setIsBusy(true)
    setNotice(null)
    try {
      const parsed = document ?? await parseCurrentText(text)
      const nextDocument: ScriptDocument = {
        ...parsed,
        title: parsed.title === "Kịch bản chưa đặt tên" ? "Kịch bản cảm xúc" : parsed.title,
        defaults: { ...parsed.defaults, voice_id: activeVoiceId, global_delivery_prompt: globalPrompt || null },
        speakers: parsed.speakers.map((speaker) => ({ ...speaker, voice_id: speaker.voice_id || activeVoiceId })),
      }
      setDocument(nextDocument)
      const saved = await apiFetch<{ id: string }>("/api/v1/scripts", {
        method: "POST",
        body: JSON.stringify({ document: nextDocument, title: nextDocument.title }),
      })
      const nextRender = await apiFetch<ScriptRender>(`/api/v1/scripts/${saved.id}/renders`, {
        method: "POST",
        body: JSON.stringify({ scope: "stale", output_format: outputFormat }),
      })
      setRender(nextRender)
      setNotice({ tone: "info", text: "Đã đưa kịch bản vào hàng đợi riêng. Tạo âm thanh vẫn giữ ưu tiên." })
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Không thể tạo audio cho kịch bản." })
    } finally {
      setIsBusy(false)
    }
  }

  const handleCancel = async () => {
    if (!render) return
    try {
      const next = await apiFetch<ScriptRender>(`/api/v1/script-renders/${render.id}/cancel`, { method: "POST" })
      setRender(next)
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Không thể hủy render." })
    }
  }

  const handleRetry = async (scope = "failed") => {
    if (!render) return
    try {
      const next = await apiFetch<ScriptRender>(`/api/v1/script-renders/${render.id}/retry`, {
        method: "POST",
        body: JSON.stringify({ scope }),
      })
      setRender(next)
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Không thể thử lại segment." })
    }
  }

  const insertTag = (tag: string) => {
    setText((current) => `${current}${current && !current.endsWith(" ") ? " " : ""}${tag} `)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto pb-6">
      <header className="flex shrink-0 flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.22em] text-muted-foreground">VieNeu v3 Turbo · Script workspace</p>
          <h1 className="text-3xl font-black tracking-[-0.04em] text-foreground">Kịch bản cảm xúc</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Từ một trang kịch bản đến bản thu hoàn chỉnh — giữ nguyên giọng, làm rõ nhịp diễn.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-2 text-xs font-bold shadow-sm">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          VieNeu sẵn sàng
        </div>
      </header>

      {notice && (
        <div className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${notice.tone === "error" ? "border-red-200 bg-red-50 text-red-800" : notice.tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"}`} role="status">
          {notice.tone === "error" ? <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" /> : <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />}
          <span>{notice.text}</span>
        </div>
      )}

      <div className="grid min-h-0 shrink-0 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="min-w-0 space-y-5">
          <div className="overflow-hidden rounded-[1.6rem] border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="min-w-0">
                <p className="text-sm font-extrabold">Quick Input</p>
                <p className="mt-1 text-xs text-muted-foreground">Dán văn bản, thêm delivery tag, rồi tạo ngay.</p>
              </div>
              <button type="button" onClick={() => fileInputRef.current?.click()} className="inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-bold text-muted-foreground transition hover:border-foreground hover:text-foreground" disabled={isBusy}>
                <FileUp className="h-4 w-4" /> Nhập TXT / SRT
              </button>
              <input ref={fileInputRef} type="file" accept=".txt,.srt,text/plain" className="hidden" onChange={(event) => event.target.files?.[0] && handleImport(event.target.files[0])} />
            </div>
            <div className="p-4">
              <textarea
                value={text}
                onChange={(event) => { setText(event.target.value); setDocument(null); setRender(null) }}
                placeholder="Dán nội dung hoặc kịch bản…\n\n[sợ hãi] Linh nghe thấy tiếng động phía sau.\n\nNam: [bình tĩnh] Chỉ là gió thôi."
                maxLength={10000}
                className="min-h-[360px] w-full resize-y rounded-2xl bg-muted/40 p-5 font-mono text-[14px] leading-7 text-foreground outline-none ring-1 ring-transparent transition placeholder:text-muted-foreground/60 focus:bg-background focus:ring-primary/20"
                disabled={isBusy}
              />
              <div className="flex flex-wrap items-center justify-between gap-2 px-1 pt-3 text-[11px] font-bold text-muted-foreground">
                <span>{text.length.toLocaleString("vi-VN")} / 10.000 ký tự</span>
                <span>{lineCount} đoạn · {tagCounts.total} tag</span>
              </div>
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-extrabold">Ngữ điệu toàn bài <span className="font-normal text-muted-foreground">(tùy chọn)</span></p>
                <p className="mt-1 text-xs text-muted-foreground">Đây là chỉ dẫn sáng tạo của Void Melody; cảm xúc không phải tham số native của VieNeu.</p>
              </div>
              <Sparkles className="h-4 w-4 text-amber-500" />
            </div>
            <input value={globalPrompt} onChange={(event) => setGlobalPrompt(event.target.value)} placeholder="Kể chuyện trầm, chậm rãi, hơi bí ẩn…" className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none transition focus:border-foreground" />
          </div>

          <div className="rounded-[1.6rem] border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm font-extrabold">Delivery tags</p>
                <p className="mt-1 text-xs text-muted-foreground">Native cue được gửi đúng dạng VieNeu; intent khác chỉ là xấp xỉ an toàn.</p>
              </div>
              <span className="rounded-full bg-muted px-3 py-1 text-[11px] font-bold text-muted-foreground">{tagCounts.native} native · {tagCounts.approximated} xấp xỉ</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {tagOptions.map((tag) => (
                <button key={tag.value} type="button" onClick={() => insertTag(tag.value)} className={`rounded-full border px-3 py-1.5 text-xs font-bold transition hover:-translate-y-0.5 ${tag.kind === "native" ? "border-emerald-200 bg-emerald-50 text-emerald-800 hover:border-emerald-400" : tag.kind === "unsupported" ? "border-slate-200 bg-slate-50 text-slate-500 hover:border-slate-400" : "border-amber-200 bg-amber-50 text-amber-900 hover:border-amber-400"}`}>
                  <span className="mr-1.5 opacity-70">{tag.kind === "native" ? "✓" : tag.kind === "unsupported" ? "×" : "≈"}</span>{tag.label}
                </button>
              ))}
            </div>
          </div>

          {reviewOpen && (
            <div className="rounded-[1.6rem] border border-border bg-card p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-extrabold">Review & mapping</p>
                  <p className="mt-1 text-xs text-muted-foreground">Gán giọng một lần cho mỗi nhân vật. Kịch bản luôn giữ cùng document model.</p>
                </div>
                <button type="button" onClick={() => setReviewOpen(false)} className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"><ChevronDown className="h-4 w-4" /></button>
              </div>
              {document?.speakers.length ? (
                <div className="space-y-3">
                  {document.speakers.map((speaker) => (
                    <div key={speaker.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 p-3">
                      <div><p className="text-sm font-bold">{speaker.name}</p><p className="text-[11px] text-muted-foreground">Nhân vật</p></div>
                      <select value={speaker.voice_id || activeVoiceId} onChange={(event) => assignSpeaker(speaker.id, event.target.value)} className="min-w-[220px] rounded-lg border border-border bg-background px-3 py-2 text-xs font-semibold outline-none">
                        {voices.map((voice) => <option key={voice.voiceType} value={voice.voiceType}>{voice.displayName}{customVoices?.items.some((custom) => custom.id === voice.voiceType) ? " · Clone" : " · Preset"}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              ) : <p className="rounded-xl bg-muted/50 px-4 py-3 text-xs text-muted-foreground">Chưa phát hiện nhân vật riêng; toàn bài dùng giọng mặc định.</p>}
              <div className="mt-4 space-y-2">
                {document?.scenes.flatMap((scene) => scene.lines).slice(0, 6).map((line) => (
                  <div key={line.id} className="flex items-start gap-3 rounded-xl bg-muted/35 px-3 py-2.5 text-xs"><span className="mt-0.5 w-16 shrink-0 font-mono text-[10px] text-muted-foreground">{line.id}</span><span className="flex-1 leading-5">{line.text}</span><span className="rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold text-amber-900">{line.delivery.intent}</span></div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className="space-y-5">
          <div className="rounded-[1.6rem] border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between"><p className="text-sm font-extrabold">Giọng đọc</p><span className="rounded-full bg-muted px-2.5 py-1 text-[10px] font-black uppercase tracking-wider">VieNeu</span></div>
            <select value={activeVoiceId} onChange={(event) => setSelectedVoice(event.target.value)} className="w-full appearance-none rounded-xl border border-border bg-background px-4 py-3 text-sm font-bold outline-none focus:border-foreground" disabled={isBusy}>
              <option value="" disabled>Chọn giọng đọc</option>
              {voices.map((voice) => <option key={voice.voiceType} value={voice.voiceType}>{voiceLabel(voice)}{customVoices?.items.some((custom) => custom.id === voice.voiceType) ? " · Clone" : ""}</option>)}
            </select>
            {isClone && <div className="mt-3 flex gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-[11px] leading-5 text-amber-900"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />Cảm xúc ngoài cười, thở dài, hắng giọng là xấp xỉ và phụ thuộc audio mẫu.</div>}
          </div>

          <div className="rounded-[1.6rem] border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between"><p className="text-sm font-extrabold">Output</p><span className="text-xs text-muted-foreground">48 kHz · mono</span></div>
            <div className="grid grid-cols-2 gap-2">
              {(["mp3", "wav"] as const).map((format) => <button key={format} type="button" onClick={() => setOutputFormat(format)} className={`rounded-xl border px-3 py-2.5 text-xs font-black uppercase tracking-wider transition ${outputFormat === format ? "border-foreground bg-foreground text-background" : "border-border bg-background text-muted-foreground hover:border-foreground"}`}>{format}</button>)}
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-foreground/10 bg-foreground p-5 text-background shadow-sm">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-background/50">Render preflight</p>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div><p className="text-2xl font-black tracking-tight">{lineCount}</p><p className="text-[11px] text-background/55">đoạn cần tạo</p></div>
              <div><p className="text-2xl font-black tracking-tight">{speakerCount || 1}</p><p className="text-[11px] text-background/55">nhân vật</p></div>
            </div>
            <div className="mt-5 space-y-2 border-t border-background/15 pt-4 text-[11px] text-background/70">
              <p className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-300" />3 native cues được hỗ trợ</p>
              <p className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-300" />Cache theo từng segment</p>
              <p className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-300" />Không tạo job TTS thường</p>
            </div>
            <div className="mt-5 grid gap-2">
              <button type="button" onClick={() => setReviewOpen((value) => !value)} className="flex items-center justify-center gap-2 rounded-xl border border-background/20 px-4 py-3 text-xs font-black transition hover:bg-background/10"><span>{reviewOpen ? "Đóng review" : "Review script"}</span><ArrowRight className="h-3.5 w-3.5" /></button>
              <button type="button" onClick={handleGenerate} disabled={isBusy || !text.trim() || !activeVoiceId} className="flex items-center justify-center gap-2 rounded-xl bg-background px-4 py-3 text-xs font-black text-foreground transition hover:bg-background/90 disabled:cursor-not-allowed disabled:opacity-40">
                {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} {isBusy ? "Đang chuẩn bị…" : "Tạo audio"}
              </button>
            </div>
          </div>

          {render && <div className="rounded-[1.6rem] border border-border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-extrabold">Render hiện tại</p><p className="mt-1 text-xs text-muted-foreground">{render.status === "completed" ? "Bản thu đã sẵn sàng." : render.status === "partial_failed" ? "Một số đoạn cần thử lại." : render.status === "cancelled" ? "Render đã hủy, cache vẫn được giữ." : "Đang xử lý theo từng segment."}</p></div><span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase ${render.status === "completed" ? "bg-emerald-100 text-emerald-800" : render.status === "failed" || render.status === "partial_failed" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>{render.status}</span></div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-foreground transition-all" style={{ width: `${render.progress}%` }} /></div>
            <div className="mt-2 flex justify-between text-[11px] font-bold text-muted-foreground"><span>{render.completed_segments}/{render.total_segments} segment</span><span>{render.progress}%</span></div>
            <div className="mt-4 space-y-1.5">{render.segments.slice(0, 5).map((segment) => <div key={segment.id} className="flex items-center justify-between gap-2 text-[11px]"><span className="truncate text-muted-foreground">{segment.line_id}</span><span className="font-bold">{segmentLabel(segment)}</span></div>)}</div>
            <div className="mt-4 flex flex-wrap gap-2">
              {(render.status === "rendering" || render.status === "queued" || render.status === "planning") && <button type="button" onClick={handleCancel} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[11px] font-bold"><Pause className="h-3.5 w-3.5" /> Hủy</button>}
              {(render.status === "failed" || render.status === "partial_failed" || render.status === "cancelled") && <button type="button" onClick={() => handleRetry("failed")} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[11px] font-bold"><RotateCcw className="h-3.5 w-3.5" /> Thử lại lỗi</button>}
              {render.status === "completed" && render.output_url && (
                audioBlobUrl ? (
                  <div className="w-full space-y-2">
                    <audio controls preload="metadata" src={audioBlobUrl} className="w-full" />
                    <a href={audioBlobUrl} download={`script-${render.id}.${render.output_format}`} className="inline-flex items-center gap-1.5 rounded-lg bg-foreground px-3 py-2 text-[11px] font-bold text-background"><Download className="h-3.5 w-3.5" /> Tải xuống</a>
                  </div>
                ) : (
                  <p className={`text-[11px] font-semibold ${audioLoadError ? "text-destructive" : "text-muted-foreground"}`} role={audioLoadError ? "alert" : undefined}>{audioLoadError ? `Không thể tải audio: ${audioLoadError}` : "Đang tải audio…"}</p>
                )
              )}
            </div>
          </div>}
        </aside>
      </div>
      <footer className="flex shrink-0 flex-wrap items-center justify-center gap-x-2 gap-y-1 pt-1 text-center text-[11px] leading-5 text-muted-foreground">
        <UploadCloud className="h-3.5 w-3.5 shrink-0" />
        <span>TXT / SRT tối đa 20 MB · Parse cục bộ theo cấu trúc rõ ràng · Không gửi script vào History</span>
      </footer>
    </div>
  )
}
