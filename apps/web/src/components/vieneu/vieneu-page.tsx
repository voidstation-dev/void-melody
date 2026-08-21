"use client"

import { ChangeEvent, DragEvent, SyntheticEvent, useEffect, useRef, useState } from "react"
import { AudioLines, Check, FileAudio, Mic2, ShieldCheck, Sparkles, Upload, UserRoundPlus } from "lucide-react"
import { useVoiceCapabilities } from "@/hooks/use-voice-capabilities"
import { useVoiceLab } from "@/hooks/use-voice-lab"
import { useTTSJob } from "@/hooks/use-tts-job"
import { useCustomVoice } from "@/hooks/use-custom-voice"
import { apiFetch } from "@/lib/api-client"
import { BatchJobCreateResponse } from "@/types/tts-job"
import { useTranslation } from "@/hooks/use-translation"

type Section = "voices" | "cloning"

const ACCEPTED_AUDIO = ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a"]
const ACCEPTED_EXTENSIONS = [".wav", ".mp3", ".m4a"]
const MAX_FILE_BYTES = 50 * 1024 * 1024

function formatBytes(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function RuntimeBadge({ isLoading, available, reason, isVi }: { isLoading: boolean; available: boolean; reason?: string | null; isVi: boolean }) {
  if (isLoading) return <span className="rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground">{isVi ? "Đang kiểm tra động cơ…" : "Checking runtime…"}</span>
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${available ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400" : "border-amber-200 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"}`} title={reason ?? undefined}><span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${available ? "bg-emerald-500" : "bg-amber-500"}`} />{available ? (isVi ? "Sẵn sàng nhân bản" : "Clone ready") : (isVi ? "Chưa sẵn sàng" : "Clone unavailable")}</span>
}

function StepCard({ step, title, children }: { step: string; title: string; children: React.ReactNode }) {
  return <section className="rounded-2xl border border-border bg-card p-5 shadow-sm"><div className="mb-4 flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">{step}</span><h2 className="text-base font-bold">{title}</h2></div>{children}</section>
}

function Waveform({ peaks = [] }: { peaks?: number[] }) {
  const bars = peaks.length ? peaks : [24, 42, 30, 64, 48, 78, 54, 36, 70, 46, 82, 58, 32, 66, 44, 74, 40, 60, 28, 52, 38, 72, 48, 34, 68, 44, 76, 56, 32, 62, 42, 70]
  return <div className="flex h-24 items-center gap-1 rounded-xl border border-dashed border-border bg-muted/40 p-3" aria-label="Audio waveform preview">{bars.map((height, index) => <span key={index} className="w-full rounded-full bg-muted-foreground/25" style={{ height: `${height}%` }} />)}</div>
}

export function VieneuPage({ initialVoiceId = null }: { initialVoiceId?: string | null } = {}) {
  const { t, isVi } = useTranslation();
  const [section, setSection] = useState<Section>(initialVoiceId ? "cloning" : "voices")
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [voiceName, setVoiceName] = useState("")
  const [consent, setConsent] = useState(false)
  const [previewText, setPreviewText] = useState("")
  const [previewRate, setPreviewRate] = useState("1")
  const [previewJobId, setPreviewJobId] = useState<string | null>(null)
  const [selectedSegment, setSelectedSegment] = useState<{ start: number; end: number } | null>(null)
  const [fileUrl, setFileUrl] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const sourceAudioRef = useRef<HTMLAudioElement>(null)
  const capabilities = useVoiceCapabilities()
  const { analysis: analysisMutation, clone: cloneMutation } = useVoiceLab()
  const runtime = capabilities.data
  const analysis = analysisMutation.data
  const selectedProfile = useCustomVoice(initialVoiceId)
  const profile = cloneMutation.data ?? selectedProfile.data
  const { data: previewJob, isError: previewJobError } = useTTSJob(previewJobId)
  const cloneAvailable = runtime?.supports_voice_cloning === true
  const sourceDuration = analysis?.source_duration_seconds ?? analysis?.duration_seconds ?? 0
  const selectedStart = selectedSegment?.start ?? analysis?.selected_start_seconds ?? 0
  const selectedEnd = selectedSegment?.end ?? analysis?.selected_end_seconds ?? 0
  const cloneAnalysis = analysis && {
    ...analysis,
    selected_start_seconds: selectedStart,
    selected_end_seconds: selectedEnd,
  }

  useEffect(() => () => {
    if (fileUrl && typeof URL.revokeObjectURL === "function") {
      URL.revokeObjectURL(fileUrl)
    }
  }, [fileUrl])

  const readableError = (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback

  const playSelection = () => {
    const audio = sourceAudioRef.current
    if (!audio || !selectedEnd || selectedEnd <= selectedStart) return
    audio.currentTime = selectedStart
    void audio.play()
  }

  const handleAudioTimeUpdate = (event: SyntheticEvent<HTMLAudioElement>) => {
    const audio = event.currentTarget
    if (selectedEnd > selectedStart && audio.currentTime >= selectedEnd) {
      audio.pause()
      audio.currentTime = selectedStart
    }
  }

  const selectFile = (nextFile: File | undefined) => {
    if (!nextFile) return
    const extension = `.${nextFile.name.split(".").pop()?.toLowerCase()}`
    if (!ACCEPTED_EXTENSIONS.includes(extension) || (nextFile.type && !ACCEPTED_AUDIO.includes(nextFile.type))) {
      setFile(null)
      setFileError(isVi ? "Vui lòng chọn file âm thanh WAV, MP3 hoặc M4A." : "Choose a WAV, MP3, or M4A audio file.")
      return
    }
    if (nextFile.size > MAX_FILE_BYTES) {
      setFile(null)
      setFileError(isVi ? "Dung lượng file âm thanh phải nhỏ hơn 50 MB." : "Audio files must be smaller than 50 MB.")
      return
    }
    setFileError(null)
    setFileUrl(typeof URL.createObjectURL === "function" ? URL.createObjectURL(nextFile) : null)
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
    setPreviewError(null)
    try {
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
    } catch (error) {
      setPreviewError(readableError(error, isVi ? "Không thể tạo tác vụ nghe thử." : "Preview could not be queued."))
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="mb-5 flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.18em] text-primary/60">VieNeu / local audio</p>
          <h1 className="text-2xl font-bold tracking-tight">{t("voiceLab.title")}</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">{t("voiceLab.subtitle")}</p>
        </div>
        <RuntimeBadge isLoading={capabilities.isLoading} available={cloneAvailable} reason={runtime?.reason} isVi={isVi} />
      </header>

      <div className="mb-5 flex shrink-0 items-center justify-between gap-4">
        <div className="inline-flex rounded-xl border border-border bg-card p-1 shadow-sm" role="tablist" aria-label="Voice Lab sections">
          <button
            type="button"
            role="tab"
            aria-selected={section === "cloning"}
            onClick={() => setSection("cloning")}
            className={`rounded-lg px-4 py-2 text-sm font-bold transition-colors ${section === "cloning" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
          >
            {t("voiceLab.tabClone")}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={section === "voices"}
            onClick={() => setSection("voices")}
            className={`rounded-lg px-4 py-2 text-sm font-bold transition-colors ${section === "voices" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
          >
            {t("voiceLab.tabPresets")}
          </button>
        </div>
        <span className="hidden text-xs text-muted-foreground sm:block">V3 Turbo · 48 kHz</span>
      </div>

      {section === "voices" ? (
        <div className="flex min-h-0 flex-1 items-center justify-center rounded-2xl border border-dashed border-border bg-card p-10 text-center shadow-sm">
          <div className="max-w-md">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Mic2 className="h-7 w-7" />
            </div>
            <h2 className="mt-5 text-lg font-bold">{t("voiceLab.tabPresets")}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {isVi ? "Khám phá danh sách giọng đọc tiếng Việt phong phú tại Thư viện giọng, hoặc tạo hồ sơ giọng riêng từ mẫu âm thanh của bạn." : "Browse the built-in Vietnamese voices in Voice Library, or create a reusable profile from your own sample."}
            </p>
            <a
              href="/voices"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground transition-opacity hover:opacity-90 shadow-xs"
            >
              <AudioLines className="h-4 w-4" />
              <span>{isVi ? "Mở Thư viện giọng" : "Open Voice Library"}</span>
            </a>
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-5">
              {/* STEP 1 */}
              <StepCard step="1" title={t("voiceLab.step1Title")}>
                <div
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={onDrop}
                  className={`rounded-xl border border-dashed p-5 text-center transition-colors ${file ? "border-primary/40 bg-primary/[0.03]" : "border-border bg-muted/30 hover:border-primary/50"}`}
                >
                  <input
                    ref={fileInputRef}
                    id="voice-sample-file"
                    aria-label="Voice sample file"
                    type="file"
                    accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4"
                    onChange={onFileChange}
                    className="sr-only"
                  />
                  {file ? (
                    <div className="flex items-center justify-between gap-3 text-left">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                          <FileAudio className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-bold">{file.name}</p>
                          <p className="text-xs text-muted-foreground">{formatBytes(file.size)} · {isVi ? "Xử lý cục bộ" : "Local only"}</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => { setFile(null); setFileUrl(null); setFileError(null) }}
                        className="shrink-0 text-xs font-semibold text-muted-foreground underline underline-offset-2 hover:text-foreground"
                      >
                        {isVi ? "Đổi file" : "Replace"}
                      </button>
                    </div>
                  ) : (
                    <>
                      <Upload className="mx-auto h-6 w-6 text-primary/70" />
                      <p className="mt-3 text-sm font-semibold">{t("voiceLab.step1Dropzone")}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{t("voiceLab.step1Formats")}</p>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="mt-4 rounded-lg border border-border bg-card px-4 py-2 text-xs font-bold shadow-xs hover:bg-muted"
                      >
                        {t("voiceLab.step1Browse")}
                      </button>
                    </>
                  )}
                </div>
                {fileUrl && (
                  <div className="mt-3 rounded-xl border border-border bg-card p-3">
                    <p className="mb-2 text-xs font-semibold text-muted-foreground">{isVi ? "Phát lại nguồn âm thanh" : "Source playback"}</p>
                    <audio ref={sourceAudioRef} className="w-full" controls src={fileUrl} onTimeUpdate={handleAudioTimeUpdate} />
                  </div>
                )}
                {fileError && <p className="mt-3 text-xs font-semibold text-destructive" role="alert">{fileError}</p>}
                <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span>{isVi ? "Âm thanh được xử lý hoàn toàn trên máy tính của bạn, không gửi lên máy chủ bên ngoài." : "Audio is processed locally and never uploaded."}</span>
                </div>
              </StepCard>

              {/* STEP 2 */}
              <StepCard step="2" title={t("voiceLab.step2Title")}>
                {file ? (
                  <>
                    <div className="mb-3 flex flex-wrap gap-2 text-xs">
                      <span className={`rounded-full px-2.5 py-1 font-semibold ${analysisMutation.isError ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400" : analysisMutation.isPending ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400" : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"}`}>
                        {analysisMutation.isError ? (isVi ? "Phân tích thất bại" : "Analysis failed") : analysisMutation.isPending ? (isVi ? "Đang phân tích…" : "Analyzing…") : analysis ? (isVi ? "Phân tích xong" : "Analysis ready") : (isVi ? "Chờ phân tích" : "Analysis pending")}
                      </span>
                      <span className="rounded-full bg-muted px-2.5 py-1 font-semibold text-muted-foreground">
                        {isVi ? "Đoạn đã chọn: " : "Selected segment: "}
                        {analysis ? `${selectedStart.toFixed(1)}–${selectedEnd.toFixed(1)}s` : "—"}
                      </span>
                    </div>
                    {analysisMutation.isError && (
                      <p className="mb-3 text-xs font-semibold text-destructive" role="alert">
                        {readableError(analysisMutation.error, isVi ? "Phân tích thất bại. Vui lòng đảm bảo file mẫu dài ít nhất 3 giây." : "Audio analysis failed. Check that the sample is at least 3 seconds long.")}
                      </p>
                    )}
                    <Waveform peaks={analysis?.waveform_peaks} />
                    {analysis && (
                      <div className="mt-4 rounded-xl border border-border bg-muted/20 p-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold">{isVi ? "Đoạn mẫu trích xuất" : "Reference segment"}</span>
                          <span className="font-bold text-primary">{selectedEnd - selectedStart > 0 ? `${(selectedEnd - selectedStart).toFixed(1)}s` : "—"} · 3–8s</span>
                        </div>
                        <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground">
                          <span>0.0s</span>
                          <span>{sourceDuration.toFixed(1)}s {isVi ? "nguồn" : "source"}</span>
                        </div>
                        <button
                          type="button"
                          onClick={playSelection}
                          disabled={!fileUrl || selectedEnd <= selectedStart}
                          className="mt-3 rounded-lg border border-border bg-card px-3 py-2 text-xs font-bold disabled:opacity-40"
                        >
                          {isVi ? "Phát đoạn đã chọn" : "Play selected segment"}
                        </button>
                        <label className="mt-3 block text-xs text-muted-foreground">
                          {isVi ? "Điểm bắt đầu: " : "Start: "}{selectedStart.toFixed(1)}s
                          <input
                            aria-label="Reference segment start"
                            type="range"
                            min="0"
                            max={Math.max(0, Math.min(selectedEnd - 3, sourceDuration - 3))}
                            step="0.1"
                            value={selectedStart}
                            onChange={(event) => setSelectedSegment({ start: Math.min(Number(event.target.value), selectedEnd - 3), end: selectedEnd })}
                            className="mt-2 w-full accent-primary"
                          />
                        </label>
                        <label className="mt-3 block text-xs text-muted-foreground">
                          {isVi ? "Điểm kết thúc: " : "End: "}{selectedEnd.toFixed(1)}s
                          <input
                            aria-label="Reference segment end"
                            type="range"
                            min={Math.min(sourceDuration, selectedStart + 3)}
                            max={Math.min(sourceDuration, selectedStart + 8)}
                            step="0.1"
                            value={selectedEnd}
                            onChange={(event) => setSelectedSegment({ start: selectedStart, end: Number(event.target.value) })}
                            className="mt-2 w-full accent-primary"
                          />
                        </label>
                      </div>
                    )}
                    <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                      {[
                        [isVi ? "Giọng nói" : "Speech", analysis ? `${Math.round(analysis.speech_ratio * 100)}%` : "—"],
                        [isVi ? "Độ ồn" : "Noise", analysis ? `${analysis.noise_level_db} dB` : "—"],
                        [isVi ? "Cắt đỉnh" : "Clipping", analysis ? `${(analysis.clipping_ratio * 100).toFixed(1)}%` : "—"],
                        [isVi ? "Chất lượng" : "Quality", analysis ? `${analysis.quality_score}/100` : "—"]
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-xl bg-card border border-border/60 p-2.5">
                          <p className="text-muted-foreground text-[11px]">{label}</p>
                          <p className="mt-1 font-bold text-foreground text-sm">{value}</p>
                        </div>
                      ))}
                    </div>
                    {analysis?.warnings.map((warning) => (
                      <p key={warning} className="mt-3 text-xs font-semibold text-amber-700 dark:text-amber-400">{warning}</p>
                    ))}
                  </>
                ) : (
                  <div className="flex min-h-24 items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 text-center text-sm text-muted-foreground">
                    {isVi ? "Tải lên mẫu âm thanh để hiển thị biểu đồ sóng và đoạn trích xuất gợi ý." : "Upload a sample to see its waveform and recommended reference segment."}
                  </div>
                )}
              </StepCard>

              {/* STEP 3 */}
              <StepCard step="3" title={t("voiceLab.step3Title")}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="text-xs font-semibold">
                    {t("voiceLab.voiceNameLabel")}
                    <input
                      value={voiceName}
                      onChange={(event) => setVoiceName(event.target.value)}
                      placeholder={t("voiceLab.voiceNamePlaceholder")}
                      className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none ring-primary/20 focus:ring-4"
                    />
                  </label>
                  <label className="text-xs font-semibold">
                    {t("voiceLab.languageLabel")}
                    <input
                      value={isVi ? "Tiếng Việt" : "Vietnamese"}
                      readOnly
                      className="mt-2 w-full rounded-lg border border-border bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground outline-none"
                    />
                  </label>
                </div>
                <div className="mt-4 flex items-center justify-between rounded-xl border border-border bg-muted/30 p-3 text-xs">
                  <span className="font-semibold">{t("voiceLab.engineLabel")}</span>
                  <span className="font-bold">VieNeu v3 Turbo · {runtime?.backend ?? "—"}</span>
                </div>
                <label className="mt-4 flex items-start gap-3 text-xs leading-5 text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(event) => setConsent(event.target.checked)}
                    className="mt-1 h-4 w-4 accent-primary"
                  />
                  <span>{t("voiceLab.consentText")}</span>
                </label>
                <button
                  type="button"
                  onClick={() => file && cloneAnalysis && cloneMutation.mutate({ file, displayName: voiceName, consentGiven: consent, analysis: cloneAnalysis })}
                  disabled={!cloneAvailable || !file || !cloneAnalysis || !voiceName.trim() || !consent || cloneMutation.isPending}
                  className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-foreground transition-opacity disabled:cursor-not-allowed disabled:opacity-40 shadow-xs"
                >
                  <UserRoundPlus className="h-4 w-4" />
                  <span>{cloneMutation.isPending ? t("voiceLab.creatingVoice") : t("voiceLab.createVoiceBtn")}</span>
                </button>
                {!cloneAvailable && (
                  <p className="mt-3 text-xs font-semibold text-amber-700 dark:text-amber-400">
                    {runtime?.reason ?? (isVi ? "Đang kiểm tra khả năng nhân bản trên thiết bị này." : "Checking whether this device can clone voices.")}
                  </p>
                )}
                {cloneMutation.isError && (
                  <p className="mt-3 text-xs font-semibold text-destructive" role="alert">
                    {readableError(cloneMutation.error, isVi ? "Không thể tạo hồ sơ giọng đọc. Vui lòng kiểm tra lại file mẫu." : "Voice profile could not be created. Check the sample and runtime prerequisites.")}
                  </p>
                )}
                {profile && (
                  <p className="mt-3 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                    {isVi ? "Hồ sơ giọng đã tạo thành công! Bạn có thể sử dụng lại trong " : "Voice profile ready. You can reuse it from the "}
                    <a href="/voices" className="underline underline-offset-2">{isVi ? "Thư viện giọng" : "Voice Library"}</a>.
                  </p>
                )}
              </StepCard>
            </div>

            {/* SIDEBAR: Preview & Output */}
            <aside className="h-fit rounded-2xl border border-border bg-card p-5 shadow-sm xl:sticky xl:top-0">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold">{isVi ? "Xem trước & Xuất" : "Preview & Output"}</h2>
                <Sparkles className="h-4 w-4 text-primary/60" />
              </div>
              <div className="mt-5 space-y-4 text-sm">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <span className="text-muted-foreground">{isVi ? "Nguồn mẫu" : "Reference"}</span>
                  <span className="font-semibold">{file ? (isVi ? "Đã chọn mẫu" : "Selected sample") : initialVoiceId ? (isVi ? "Hồ sơ thư viện" : "Library profile") : (isVi ? "Chưa chọn" : "Not selected")}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <span className="text-muted-foreground">{isVi ? "Phân tích" : "Analysis"}</span>
                  <span className="font-semibold">{analysis ? (isVi ? "Hoàn tất" : "Ready") : file ? (isVi ? "Đang xử lý" : "Pending") : (isVi ? "Chờ" : "Waiting")}</span>
                </div>
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <span className="text-muted-foreground">{isVi ? "Động cơ" : "Engine"}</span>
                  <span className="font-semibold">VieNeu v3 Turbo</span>
                </div>
                {selectedProfile.isLoading && initialVoiceId && (
                  <p className="rounded-xl bg-muted/50 p-3 text-xs text-muted-foreground">{isVi ? "Đang tải hồ sơ giọng…" : "Loading selected voice profile…"}</p>
                )}
                {selectedProfile.isError && (
                  <p className="rounded-xl bg-red-50 dark:bg-red-950/40 p-3 text-xs font-semibold text-destructive">{isVi ? "Không thể tải hồ sơ giọng." : "Selected voice profile could not be loaded."}</p>
                )}
                <div className="rounded-xl bg-muted/50 p-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{isVi ? "Trạng thái hồ sơ" : "Profile status"}</p>
                  <p className="mt-2 text-sm font-bold text-foreground">{profile?.display_name ?? (isVi ? "Chưa có hồ sơ" : "No profile yet")}</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {profile
                      ? (isVi ? "Đã sẵn sàng sử dụng trong Thư viện giọng và Tạo âm thanh." : "Ready to reuse in Voice Library and Melody jobs.")
                      : (isVi ? "Tạo hồ sơ giọng để mở khóa tính năng nghe thử và tạo âm thanh." : "Create a profile to unlock preview generation and reuse across Melody jobs.")}
                  </p>
                </div>
                {previewJobError && <p className="rounded-xl bg-red-50 dark:bg-red-950/40 p-3 text-xs font-semibold text-destructive">{isVi ? "Không thể tải trạng thái nghe thử." : "Preview status could not be loaded."}</p>}
                {previewError && <p className="rounded-xl bg-red-50 dark:bg-red-950/40 p-3 text-xs font-semibold text-destructive" role="alert">{previewError}</p>}
                {previewJob && (
                  <div className="rounded-xl border border-border p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{isVi ? "Bản nghe thử" : "Preview"}</p>
                    <p className="mt-2 text-sm font-semibold">
                      {previewJob.status === "completed"
                        ? (isVi ? "Bản nghe thử sẵn sàng" : "Preview ready")
                        : previewJob.status === "failed"
                          ? (previewJob.errorMessage ?? (isVi ? "Nghe thử thất bại" : "Preview failed"))
                          : `${isVi ? "Đang tạo: " : "Preview "}${previewJob.status}`}
                    </p>
                    {previewJob.audioUrl && <audio className="mt-3 w-full" controls src={previewJob.audioUrl} />}
                    {previewJob.status === "completed" && previewJob.downloadUrl && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <a href={`${previewJob.downloadUrl}?format=wav`} download className="rounded-lg border border-border px-3 py-2 text-xs font-bold hover:bg-muted transition-colors">WAV</a>
                        <a href={`${previewJob.downloadUrl}?format=mp3`} download className="rounded-lg border border-border px-3 py-2 text-xs font-bold hover:bg-muted transition-colors">MP3</a>
                        <a href={`${previewJob.downloadUrl}?format=m4a`} download className="rounded-lg border border-border px-3 py-2 text-xs font-bold hover:bg-muted transition-colors">M4A</a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </aside>
          </div>

          {/* Test synthesis section */}
          <section className="mt-5 rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              <h2 className="text-base font-bold">{isVi ? "Tạo âm thanh với giọng này" : "Generate with this Voice"}</h2>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_180px_auto] lg:items-end">
              <label className="text-xs font-semibold">
                {isVi ? "Văn bản thử nghiệm" : "Preview text"}
                <textarea
                  value={previewText}
                  onChange={(event) => setPreviewText(event.target.value)}
                  disabled={!profile}
                  placeholder={profile ? (isVi ? "Nhập một đoạn văn bản ngắn để nghe thử…" : "Type a short preview…") : (isVi ? "Vui lòng tạo hồ sơ giọng trước" : "Create a voice profile first")}
                  className="mt-2 min-h-20 w-full resize-y rounded-lg border border-border bg-muted/40 px-3 py-2.5 text-sm outline-none focus:border-primary"
                />
              </label>
              <label className="text-xs font-semibold">
                {t("generate.speed")}
                <select
                  value={previewRate}
                  onChange={(event) => setPreviewRate(event.target.value)}
                  disabled={!profile}
                  className="mt-2 w-full rounded-lg border border-border bg-muted/40 px-3 py-2.5 text-sm cursor-pointer"
                >
                  <option value="0.5">0.5×</option>
                  <option value="1">1.0×</option>
                  <option value="2">2.0×</option>
                </select>
              </label>
              <button
                type="button"
                onClick={() => void generatePreview()}
                disabled={!profile || !previewText.trim() || previewJob?.status === "queued" || previewJob?.status === "processing"}
                className="rounded-xl bg-primary px-5 py-3 text-sm font-bold text-primary-foreground disabled:opacity-40 hover:opacity-90 transition-opacity shadow-xs"
              >
                {t("voiceLab.generatePreview")}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
