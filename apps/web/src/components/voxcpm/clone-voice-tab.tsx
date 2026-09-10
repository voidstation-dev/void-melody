import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "@/hooks/use-translation"
import { AudioLines, CheckCircle2, FileAudio, Loader2, TriangleAlert, Upload, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useVoxCpmStore } from "@/stores/voxcpm-store"
import type { VoxCpmAnalysisResult } from "@/types/voxcpm"

function formatSeconds(value: number): string {
  return `${value.toFixed(1)}s`
}

function WaveformStrip({ peaks, start, end, duration }: {
  peaks: number[]
  start: number
  end: number
  duration: number
}) {
  const bars = peaks.length > 0 ? peaks : Array.from({ length: 48 }, () => 0.1)
  const selected = duration > 0 ? { start: start / duration, end: end / duration } : null
  return (
    <div className="flex h-16 items-center gap-[2px] rounded-xl border border-border bg-muted/40 px-3">
      {bars.map((peak, index) => {
        const position = (index + 0.5) / bars.length
        const inside = selected ? position >= selected.start && position <= selected.end : false
        const height = Math.max(3, Math.round(peak * 48))
        return (
          <span
            key={index}
            data-testid="voxcpm-waveform-bar"
            className="w-[3px] rounded-full"
            style={{
              height,
              backgroundColor: inside ? "var(--primary)" : "var(--muted-foreground)",
              opacity: inside ? 1 : 0.35,
            }}
          />
        )
      })}
    </div>
  )
}

function MetricPill({ label, value, testid }: { label: string; value: string; testid?: string }) {
  return (
    <div
      data-testid={testid}
      className="flex flex-col gap-1 rounded-xl border border-border bg-card px-3 py-2"
    >
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm font-bold text-foreground">{value}</span>
    </div>
  )
}

function AnalysisSection({ analysis }: { analysis: VoxCpmAnalysisResult }) {
  const { t } = useTranslation()
  const selectedStart = analysis.selected_start_seconds
  const selectedEnd = analysis.selected_end_seconds
  const [trimStart, setTrimStart] = useState(String(selectedStart))
  const [trimEnd, setTrimEnd] = useState(String(selectedEnd))

  useEffect(() => {
    setTrimStart(String(analysis.selected_start_seconds))
    setTrimEnd(String(analysis.selected_end_seconds))
  }, [analysis])

  const parsedStart = Number(trimStart) || 0
  const parsedEnd = Number(trimEnd) || 0
  const trimmedDuration = Math.max(0, parsedEnd - parsedStart)
  const isTrimValid =
    trimmedStartValid(parsedStart, parsedEnd, analysis) && trimmedEndValid(parsedEnd, analysis)

  return (
    <div className="space-y-3" data-testid="voxcpm-analysis-panel">
      <WaveformStrip
        peaks={analysis.waveform_peaks}
        start={selectedStart}
        end={selectedEnd}
        duration={analysis.source_duration_seconds}
      />
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <MetricPill
          testid="voxcpm-quality"
          label={t("voxcpm.qualityScore")}
          value={String(analysis.quality_score)}
        />
        <MetricPill
          label={t("voxcpm.noiseLevel")}
          value={`${analysis.noise_level_db.toFixed(1)} dB`}
        />
        <MetricPill
          label={t("voxcpm.speechRatio")}
          value={`${Math.round(analysis.speech_ratio * 100)}%`}
        />
        <MetricPill
          label={t("voxcpm.clipping")}
          value={`${(analysis.clipping_ratio * 100).toFixed(2)}%`}
        />
      </div>
      {analysis.warnings.length > 0 && (
        <ul className="space-y-1 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
          {analysis.warnings.map((warning) => (
            <li key={warning} className="flex items-start gap-2">
              <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <div className="space-y-1">
          <label htmlFor="voxcpm-trim-start" className="text-xs text-muted-foreground">
            {t("voxcpm.trimStart")}
          </label>
          <Input
            id="voxcpm-trim-start"
            type="number"
            step="0.1"
            min={0}
            max={analysis.source_duration_seconds}
            value={trimStart}
            onChange={(event) => setTrimStart(event.target.value)}
            className="rounded-xl"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="voxcpm-trim-end" className="text-xs text-muted-foreground">
            {t("voxcpm.trimEnd")}
          </label>
          <Input
            id="voxcpm-trim-end"
            type="number"
            step="0.1"
            min={0}
            max={analysis.source_duration_seconds}
            value={trimEnd}
            onChange={(event) => setTrimEnd(event.target.value)}
            className="rounded-xl"
          />
        </div>
        <div className="flex items-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full rounded-xl"
            onClick={() => {
              const recommendedStart = analysis.recommended_start_seconds ?? analysis.selected_start_seconds
              const recommendedEnd = analysis.recommended_end_seconds ?? analysis.selected_end_seconds
              setTrimStart(String(recommendedStart))
              setTrimEnd(String(recommendedEnd))
            }}
          >
            {t("voxcpm.useRecommended")}
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        {t("voxcpm.referenceDuration")}: {formatSeconds(isTrimValid ? parsedEnd - parsedStart : 0)}
      </p>
      <span data-testid="voxcpm-trim-valid" className="hidden">
        {isTrimValid ? "valid" : "invalid"}
      </span>
    </div>
  )
}

function trimmedStartValid(start: number, end: number, analysis: VoxCpmAnalysisResult): boolean {
  return (
    Number.isFinite(start) &&
    start >= 0 &&
    end > start &&
    start < analysis.source_duration_seconds
  )
}

function trimmedEndValid(end: number, analysis: VoxCpmAnalysisResult): boolean {
  return Number.isFinite(end) && end <= analysis.source_duration_seconds + 0.01
}

/** Clone voice tab: upload → analyze → trim → create cloned voice (Phase 3). */
export function CloneVoiceTab() {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [displayName, setDisplayName] = useState("")
  const [description, setDescription] = useState("")
  const [transcript, setTranscript] = useState("")
  const [consent, setConsent] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const analysis = useVoxCpmStore((state) => state.analysis)
  const isAnalyzing = useVoxCpmStore((state) => state.isAnalyzing)
  const isCreatingVoice = useVoxCpmStore((state) => state.isCreatingVoice)
  const cloneError = useVoxCpmStore((state) => state.cloneError)
  const analyzeReference = useVoxCpmStore((state) => state.analyzeReference)
  const submitCloneVoice = useVoxCpmStore((state) => state.submitCloneVoice)
  const clearAnalysis = useVoxCpmStore((state) => state.clearAnalysis)

  const analysisTrim = useMemo(
    () => (analysis ? { start: analysis.selected_start_seconds, end: analysis.selected_end_seconds } : null),
    [analysis],
  )

  useEffect(() => () => clearAnalysis(), [clearAnalysis])

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null
    event.target.value = ""
    if (!selected) return
    setFile(selected)
    setLocalError(null)
    await analyzeReference(selected)
  }

  const canSubmit =
    file !== null && analysis !== null && displayName.trim().length > 0 && consent && !isCreatingVoice

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitted(true)
    if (!file || !analysis || !canSubmit) return
    const ok = await submitCloneVoice({
      file,
      displayName: displayName.trim(),
      consentGiven: consent,
      description: description.trim() || undefined,
      referenceTranscript: transcript.trim() || undefined,
    })
    if (ok) {
      setFile(null)
      setDisplayName("")
      setDescription("")
      setTranscript("")
      setConsent(false)
      setSubmitted(false)
      clearAnalysis()
    }
  }

  return (
    <div className="space-y-4" data-testid="voxcpm-clone-tab">
      <input
        ref={fileInputRef}
        type="file"
        accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4"
        className="hidden"
        data-testid="voxcpm-file-input"
        onChange={handleFileChange}
      />

      {/* Section 1 — reference audio selection */}
      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h3 className="text-sm font-bold text-foreground">{t("voxcpm.cloneSectionRef")}</h3>
        <p className="mt-1 text-xs text-muted-foreground">{t("voxcpm.cloneSectionRefDesc")}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isAnalyzing}
            className="rounded-xl"
            data-testid="voxcpm-choose-file"
          >
            {isAnalyzing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {isAnalyzing
              ? t("voxcpm.analyzing")
              : file
                ? t("voxcpm.reanalyze")
                : t("voxcpm.chooseFile")}
          </Button>
          {file && (
            <span
              data-testid="voxcpm-file-name"
              className="flex items-center gap-2 rounded-xl border border-border bg-muted/40 px-3 py-2 text-xs font-medium"
            >
              <FileAudio className="h-3.5 w-3.5 text-primary" />
              {file.name}
              <button
                type="button"
                aria-label="Remove file"
                className="ml-1 text-muted-foreground transition-colors hover:text-foreground"
                onClick={() => {
                  setFile(null)
                  clearAnalysis()
                }}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </span>
          )}
        </div>
        {cloneError && (
          <p
            data-testid="voxcpm-clone-error"
            className="mt-3 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          >
            {cloneError}
          </p>
        )}
      </section>

      {/* Section 2 — waveform + trim + quality */}
      {analysis && (
        <section className="rounded-2xl border border-border bg-card p-5 shadow-sm" data-testid="voxcpm-trim-section">
          <h3 className="text-sm font-bold text-foreground">{t("voxcpm.cloneSectionTrim")}</h3>
          <p className="mt-1 text-xs text-muted-foreground">{t("voxcpm.cloneSectionTrimDesc")}</p>
          <div className="mt-4">
            <AnalysisSection analysis={analysis} />
          </div>
        </section>
      )}

      {/* Section 3 — create the clone */}
      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h3 className="text-sm font-bold text-foreground">{t("voxcpm.cloneSectionCreate")}</h3>
        <p className="mt-1 text-xs text-muted-foreground">{t("voxcpm.cloneSectionCreateDesc")}</p>
        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label htmlFor="voxcpm-voice-name" className="text-xs text-muted-foreground">
              {t("voxcpm.voiceName")}
            </label>
            <Input
              id="voxcpm-voice-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder={t("voxcpm.voiceNamePlaceholder")}
              className="rounded-xl"
              maxLength={255}
              data-testid="voxcpm-voice-name"
            />
            {submitted && displayName.trim().length === 0 && (
              <p className="text-xs text-destructive">{t("voxcpm.voiceName")}</p>
            )}
          </div>
          <div className="space-y-1">
            <label htmlFor="voxcpm-voice-description" className="text-xs text-muted-foreground">
              {t("voxcpm.voiceDescription")}
            </label>
            <Input
              id="voxcpm-voice-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder={t("voxcpm.descriptionPlaceholder")}
              className="rounded-xl"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="voxcpm-transcript" className="text-xs text-muted-foreground">
              {t("voxcpm.referenceTranscript")}
            </label>
            <Textarea
              id="voxcpm-transcript"
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
              placeholder={t("voxcpm.transcriptPlaceholder")}
              className="min-h-16 rounded-xl"
            />
          </div>
          <label
            data-testid="voxcpm-consent-row"
            className="flex items-start gap-2 rounded-xl border border-border bg-muted/30 px-3 py-2.5 text-xs"
          >
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
              className="mt-1 h-4 w-4 accent-primary"
              data-testid="voxcpm-consent"
            />
            <span className="text-muted-foreground">{t("voxcpm.consentLabel")}</span>
          </label>
          <div className="flex items-center gap-3">
            <Button
              type="submit"
              disabled={!canSubmit}
              className="rounded-xl"
              data-testid="voxcpm-create-voice"
            >
              {isCreatingVoice ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <AudioLines className="h-4 w-4" />
              )}
              {isCreatingVoice ? t("voxcpm.creatingVoice") : t("voxcpm.createVoice")}
            </Button>
            {!isCreatingVoice && analysisTrim && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                {formatSeconds(analysisTrim.end - analysisTrim.start)}
              </span>
            )}
          </div>
          {localError && <p className="text-xs text-destructive">{localError}</p>}
        </form>
      </section>
    </div>
  )
}