import { useState } from "react"
import { useSearch } from "@tanstack/react-router"
import { useAudioStudio } from "../hooks/use-audio-studio"
import { useAudioShortcuts } from "../hooks/use-audio-shortcuts"
import { AudioStudioHeader } from "./audio-studio-header"
import { ScriptEditor } from "./script-editor"
import { EmotionPanel } from "./emotion-panel"
import { VoiceSelector } from "./voice-selector"
import { SpeedControl } from "./speed-control"
import { OutputFormat } from "./output-format"
import { StudioFloatingBar } from "./studio-floating-bar"
import { JobQueueSidebar } from "@/components/tts/job-queue-sidebar"
import { useQueue } from "@/hooks/use-queue"
import { apiFetch } from "@/lib/api-client"
import { BatchJobCreateResponse } from "@/types/tts-job"
import { toast } from "sonner"
import { useTranslation } from "@/hooks/use-translation"

export function AudioStudioPage() {
  const { t } = useTranslation()
  const search = useSearch({ strict: false }) as { voice?: string }
  const voiceParam = typeof search?.voice === "string" ? search.voice : undefined

  const {
    text,
    setText,
    selectedVoiceId,
    setSelectedVoiceId,
    selectedVoice,
    allVoices,
    isLoadingVoices,
    speed,
    setSpeed,
    outputFormat,
    setOutputFormat,
    lastSavedAt,
    textareaRef,
    analysis,
    preflight,
    insertTag,
    clearText,
  } = useAudioStudio(voiceParam)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const { addToQueue } = useQueue()

  const handleGenerate = async () => {
    if (!preflight.canGenerate || isSubmitting || !selectedVoice) return

    setIsSubmitting(true)
    try {
      const voiceType = selectedVoice.voiceType || selectedVoice.id || selectedVoiceId
      const response = await apiFetch<BatchJobCreateResponse>("/api/v1/tts/jobs", {
        method: "POST",
        body: JSON.stringify({
          text,
          voiceType,
          resourceId: selectedVoice?.resourceId || undefined,
          rate: speed,
          exportFormat: outputFormat,
        }),
      })

      addToQueue(response.jobs)
      toast.success(t("audioStudio.queueSuccessToast"))
    } catch (err: unknown) {
      console.error("Failed to generate audio:", err)
      const errorMsg = (err as Error)?.message || t("errors.generateFailed")
      toast.error(errorMsg)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Keyboard shortcut binding
  useAudioShortcuts({
    onGenerate: handleGenerate,
    onSaveDraft: () => {},
    disabled: isSubmitting || !preflight.canGenerate,
  })

  const handleImportFile = async (file: File) => {
    try {
      const content = await file.text()
      if (text.trim()) {
        setText(`${text}\n\n${content}`)
      } else {
        setText(content)
      }
      toast.success(t("audioStudio.pasteSuccess"))
    } catch {
      toast.error(t("audioStudio.clipboardError"))
    }
  }

  const handleReparseFromQueue = (jobText: string) => {
    setText(jobText)
    toast.info(t("audioStudio.reloadedToast"))
  }

  return (
    <div className="flex flex-1 flex-col space-y-6 max-w-[1600px] mx-auto w-full pb-12">
      {/* Studio Header */}
      <AudioStudioHeader lastSavedAt={lastSavedAt} cueCount={analysis.totalCueCount} />

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Script Editor with Autocomplete & Full Emotion Palette (7 or 8 cols) */}
        <div className="lg:col-span-7 xl:col-span-8 flex flex-col space-y-5">
          <ScriptEditor
            text={text}
            onChange={setText}
            textareaRef={textareaRef}
            characterCount={analysis.characterCount}
            segmentCount={analysis.segments.length}
            cueCount={analysis.totalCueCount}
            disabled={isSubmitting}
            onImportFile={handleImportFile}
            onClearText={clearText}
          />

          {/* Unified Expression & Delivery Studio Palette */}
          <EmotionPanel onInsertTag={insertTag} />
        </div>

        {/* Right Column: Render Settings & Preflight (5 or 4 cols) */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-4 lg:sticky lg:top-4">
          <div className="rounded-2xl border border-border bg-card p-4 sm:p-5 shadow-sm space-y-5">
            <h2 className="text-xs font-black uppercase tracking-wider text-muted-foreground">
              {t("generate.toneProperties")}
            </h2>

            {/* Voice Selector */}
            <VoiceSelector
              selectedVoiceId={selectedVoiceId}
              onSelectVoice={setSelectedVoiceId}
              voices={allVoices}
              disabled={isLoadingVoices || isSubmitting}
            />

            {/* Speed Control */}
            <SpeedControl speed={speed} onChange={setSpeed} disabled={isSubmitting} />

            {/* Output Format */}
            <OutputFormat format={outputFormat} onChange={setOutputFormat} disabled={isSubmitting} />
          </div>

          {/* Real-time Job Queue */}
          <div className="pt-1">
            <JobQueueSidebar
              onReparseText={handleReparseFromQueue}
              currentText={text}
              compact
            />
          </div>
        </div>
      </div>

      {/* Sticky Bottom Floating Action Bar */}
      <StudioFloatingBar
        selectedVoice={selectedVoice}
        speed={speed}
        outputFormat={outputFormat}
        report={preflight}
        isSubmitting={isSubmitting}
        onGenerate={handleGenerate}
      />
    </div>
  )
}
