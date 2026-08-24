import { useState } from "react"
import { useSearch } from "@tanstack/react-router"
import { useAudioStudio } from "../hooks/use-audio-studio"
import { useAudioShortcuts } from "../hooks/use-audio-shortcuts"
import { AudioStudioHeader } from "./audio-studio-header"
import { ScriptEditor } from "./script-editor"
import { EmotionPanel } from "./emotion-panel"
import { DeliveryPanel } from "./delivery-panel"
import { VoiceSelector } from "./voice-selector"
import { SpeedControl } from "./speed-control"
import { OutputFormat } from "./output-format"
import { RenderPreflight } from "./render-preflight"
import { GenerateAudioButton } from "./generate-audio-button"
import { JobQueueSidebar } from "@/components/tts/job-queue-sidebar"
import { useQueue } from "@/hooks/use-queue"
import { apiFetch } from "@/lib/api-client"
import { BatchJobCreateResponse } from "@/types/tts-job"
import { toast } from "sonner"

export function AudioStudioPage() {
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
    if (!preflight.canGenerate || isSubmitting) return

    setIsSubmitting(true)
    try {
      const response = await apiFetch<BatchJobCreateResponse>("/api/v1/tts/jobs", {
        method: "POST",
        body: JSON.stringify({
          text,
          voiceType: selectedVoiceId,
          resourceId: selectedVoice?.resourceId || undefined,
          rate: speed,
          exportFormat: outputFormat,
        }),
      })

      addToQueue(response.jobs)
      toast.success("Đã đưa vào hàng đợi tạo audio thành công!")
    } catch (err) {
      console.error("Failed to generate audio:", err)
      toast.error("Không thể tạo audio. Vui lòng kiểm tra lại dịch vụ backend.")
    } finally {
      setIsSubmitting(false)
    }
  }

  // Keyboard shortcut binding
  useAudioShortcuts({
    onGenerate: handleGenerate,
    onSaveDraft: () => toast.success("Bản nháp đã được lưu tự động!"),
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
      toast.success(`Đã nạp nội dung từ ${file.name}`)
    } catch {
      toast.error(`Không thể đọc file ${file.name}`)
    }
  }

  const handleReparseFromQueue = (jobText: string) => {
    setText(jobText)
    toast.info("Đã nạp lại nội dung từ lịch sử hàng đợi")
  }

  return (
    <div className="flex flex-1 flex-col p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1600px] mx-auto w-full">
      {/* Studio Header */}
      <AudioStudioHeader lastSavedAt={lastSavedAt} />

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Script Editor & Expression Controls (7 or 8 cols) */}
        <div className="lg:col-span-7 xl:col-span-8 flex flex-col space-y-4">
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

          {/* Emotion & Native Cue Palette */}
          <EmotionPanel onInsertTag={insertTag} />

          {/* Advanced Delivery Controls */}
          <DeliveryPanel onInsertTag={insertTag} />
        </div>

        {/* Right Column: Render Settings & Preflight (5 or 4 cols) */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-4 lg:sticky lg:top-4">
          <div className="rounded-2xl border border-border bg-card p-4 sm:p-5 shadow-sm space-y-5">
            <h2 className="text-xs font-black uppercase tracking-wider text-muted-foreground">
              Cấu hình âm thanh
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

          {/* Render Preflight Summary */}
          <RenderPreflight report={preflight} />

          {/* Primary CTA */}
          <GenerateAudioButton
            onClick={handleGenerate}
            disabled={!preflight.canGenerate}
            isLoading={isSubmitting}
          />

          {/* Real-time Job Queue */}
          <div className="pt-2">
            <JobQueueSidebar onReparse={handleReparseFromQueue} />
          </div>
        </div>
      </div>
    </div>
  )
}
