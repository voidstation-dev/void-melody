import { useTranslation } from "@/hooks/use-translation"
import { useVoxCpmStore } from "@/stores/voxcpm-store"
import { resolveVoxCpmGenerationAudioUrl } from "@/api/voxcpm"
import { VOXCPM2_EMOTION_PRESETS } from "@/types/voxcpm"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Download, Loader2, Sparkles } from "lucide-react"

/** Phase 5: emotional TTS form wired to POST /api/v1/voxcpm/generate. */
export function EmotionalTtsTab() {
  const { t } = useTranslation()
  const emotionPresetId = useVoxCpmStore((s) => s.emotionPresetId)
  const customInstruction = useVoxCpmStore((s) => s.customInstruction)
  const targetText = useVoxCpmStore((s) => s.targetText)
  const selectedVoiceId = useVoxCpmStore((s) => s.selectedVoiceId)
  const clonedVoices = useVoxCpmStore((s) => s.clonedVoices)
  const isGenerating = useVoxCpmStore((s) => s.isGenerating)
  const generation = useVoxCpmStore((s) => s.generation)
  const generationError = useVoxCpmStore((s) => s.generationError)
  const setEmotionPreset = useVoxCpmStore((s) => s.setEmotionPreset)
  const setCustomInstruction = useVoxCpmStore((s) => s.setCustomInstruction)
  const setTargetText = useVoxCpmStore((s) => s.setTargetText)
  const setSelectedVoiceId = useVoxCpmStore((s) => s.setSelectedVoiceId)
  const generateEmotionalSpeech = useVoxCpmStore((s) => s.generateEmotionalSpeech)

  const selectedVoice = clonedVoices.find((v) => v.id === selectedVoiceId) ?? null
  const canGenerate = Boolean(selectedVoiceId) && targetText.trim().length > 0 && !isGenerating

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h2 className="mb-4 text-base font-bold">{t("voxcpm.selectedVoice")}</h2>
        <Select value={selectedVoiceId ?? ""} onValueChange={setSelectedVoiceId}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder={t("voxcpm.noVoicesYet")} />
          </SelectTrigger>
          <SelectContent>
            {clonedVoices.map((voice) => (
              <SelectItem key={voice.id} value={voice.id}>
                {voice.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selectedVoice ? (
          <p className="mt-2 text-xs text-muted-foreground">
            {t("voxcpm.referenceDuration")}: {selectedVoice.reference_duration_seconds.toFixed(1)}s · {selectedVoice.sample_rate / 1000} kHz
          </p>
        ) : null}
      </section>

      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h2 className="mb-4 text-base font-bold">{t("voxcpm.contentLabel")}</h2>
        <Textarea
          value={targetText}
          onChange={(e) => setTargetText(e.target.value)}
          placeholder={t("voxcpm.contentPlaceholder")}
          rows={5}
          className="resize-none"
        />
      </section>

      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h2 className="mb-4 text-base font-bold">{t("voxcpm.emotionPreset")}</h2>
        <Select value={emotionPresetId} onValueChange={setEmotionPreset}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {VOXCPM2_EMOTION_PRESETS.map((preset) => (
              <SelectItem key={preset.id} value={preset.id}>
                {t(preset.label as never)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {emotionPresetId === "custom" ? (
          <div className="mt-3 space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">
              {t("voxcpm.customInstruction")}
            </label>
            <Textarea
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              placeholder={t("voxcpm.customInstructionPlaceholder")}
              rows={2}
              className="resize-none"
            />
          </div>
        ) : null}
      </section>

      {generationError ? (
        <p
          data-testid="voxcpm-generate-error"
          className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {generationError}
        </p>
      ) : null}

      <div className="flex justify-end">
        <Button
          data-testid="voxcpm-generate"
          disabled={!canGenerate}
          onClick={() => void generateEmotionalSpeech()}
          className="gap-2"
        >
          {isGenerating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {isGenerating ? t("voxcpm.generating") : t("voxcpm.generate")}
        </Button>
      </div>

      {generation ? (
        <section
          data-testid="voxcpm-generation-result"
          className="rounded-2xl border border-border bg-card p-5 shadow-sm"
        >
          <h2 className="mb-3 text-base font-bold">{t("voxcpm.audioResult")}</h2>
          <audio
            controls
            src={resolveVoxCpmGenerationAudioUrl(generation.audio_url)}
            className="w-full"
          />
          <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {generation.sample_rate / 1000} kHz · {generation.duration_seconds.toFixed(1)}s
              {generation.emotion ? ` · ${generation.emotion}` : ""}
            </span>
            <a
              href={resolveVoxCpmGenerationAudioUrl(generation.audio_url)}
              download
              className="inline-flex items-center gap-1.5 text-primary hover:underline"
            >
              <Download className="h-3.5 w-3.5" />
              {t("voxcpm.downloadResult")}
            </a>
          </div>
        </section>
      ) : null}
    </div>
  )
}