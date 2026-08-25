import { Check, Cpu, Download, HardDrive, Loader2, Sparkles, Trash2, Zap } from "lucide-react"
import { useSpeechModelsStore } from "@/stores/speech-models-store"
import { WHISPER_MODEL_CATALOG, WhisperModelMetadata } from "@/types/speech-models"
import { useTranslation } from "@/hooks/use-translation"
import { useVoiceCapabilities } from "@/hooks/use-voice-capabilities"

export function SpeechModelSelector() {
  const { t } = useTranslation()
  const capabilities = useVoiceCapabilities()
  const device = capabilities.data?.device ?? "cpu"
  const isGpu = device.toLowerCase().includes("cuda") || device.toLowerCase().includes("mps") || device.toLowerCase().includes("gpu")

  const {
    activeModelId,
    installedModelIds,
    downloadingModelId,
    downloadProgress,
    autoTranscribeInVoiceLab,
    setActiveModel,
    downloadModel,
    removeModel,
    setAutoTranscribe,
  } = useSpeechModelsStore()

  return (
    <div className="mt-4 rounded-xl border border-border bg-card/60 p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h3 className="font-bold text-sm text-foreground">
              {t("settings.speechModelsTitle")}
            </h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("settings.speechModelsSubtitle")}
          </p>
        </div>

        {/* Detected Hardware Badge */}
        <div className="flex shrink-0 items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-bold text-primary">
          <Cpu className="h-3.5 w-3.5" />
          <span>{isGpu ? `GPU (${device.toUpperCase()})` : "CPU Mode"}</span>
        </div>
      </div>

      {/* Auto-transcribe in Voice Lab switch */}
      <div className="mt-4 flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3.5 py-2.5">
        <div>
          <p className="text-xs font-bold text-foreground">
            {t("settings.autoTranscribeVoiceLabLabel")}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {t("settings.autoTranscribeVoiceLabDesc")}
          </p>
        </div>
        <label className="relative inline-flex cursor-pointer items-center">
          <input
            type="checkbox"
            checked={autoTranscribeInVoiceLab}
            onChange={(e) => setAutoTranscribe(e.target.checked)}
            className="peer sr-only"
          />
          <div className="peer h-5 w-9 rounded-full bg-muted peer-checked:bg-primary peer-focus:outline-none after:absolute after:top-[2px] after:left-[2px] after:h-4 after:w-4 after:rounded-full after:bg-card after:transition-all after:content-[''] peer-checked:after:translate-x-full" />
        </label>
      </div>

      {/* Model Cards Grid */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {WHISPER_MODEL_CATALOG.map((model: WhisperModelMetadata) => {
          const isInstalled = installedModelIds.includes(model.id)
          const isActive = activeModelId === model.id
          const isDownloading = downloadingModelId === model.id

          const isRecommended =
            (isGpu && model.hardwareRecommendation === "gpu") ||
            (!isGpu && model.hardwareRecommendation === "cpu")

          return (
            <div
              key={model.id}
              className={`flex flex-col justify-between rounded-xl border p-4 transition-all ${
                isActive
                  ? "border-primary bg-primary/[0.04] shadow-xs"
                  : "border-border bg-card hover:border-border/80"
              }`}
            >
              <div>
                {/* Header & Badges */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <h4 className="font-bold text-sm text-foreground">{model.name}</h4>
                    </div>
                    <p className="text-[10px] font-mono text-muted-foreground">{model.version}</p>
                  </div>

                  <div className="flex flex-col items-end gap-1">
                    {isActive && (
                      <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                        {t("settings.activeBadge")}
                      </span>
                    )}
                    {isRecommended && (
                      <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-600 dark:text-amber-400">
                        {isGpu
                          ? t("settings.badgeRecommendedGpu")
                          : t("settings.badgeRecommendedCpu")}
                      </span>
                    )}
                  </div>
                </div>

                {/* Description */}
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {t(model.descriptionKey)}
                </p>

                {/* Specs Row */}
                <div className="mt-3 grid grid-cols-3 gap-1 rounded-lg border border-border/50 bg-muted/20 p-2 text-center text-[11px]">
                  <div>
                    <span className="text-[10px] text-muted-foreground block">
                      <HardDrive className="inline h-2.5 w-2.5 mr-0.5" />
                      Size
                    </span>
                    <span className="font-bold font-mono">{model.sizeFormatted}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">
                      <Cpu className="inline h-2.5 w-2.5 mr-0.5" />
                      RAM
                    </span>
                    <span className="font-bold font-mono">≥ {model.minRamGb} GB</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">
                      <Zap className="inline h-2.5 w-2.5 mr-0.5" />
                      {t("settings.accuracyLabel")}
                    </span>
                    <span className="font-bold font-mono text-primary">
                      {model.vietnameseAccuracy}%
                    </span>
                  </div>
                </div>

                {/* Accuracy Progress Bar */}
                <div className="mt-2.5">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary/70 transition-all duration-300"
                      style={{ width: `${model.vietnameseAccuracy}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="mt-4 pt-3 border-t border-border/60">
                {isDownloading ? (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-bold text-primary">
                      <span className="flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Đang tải...
                      </span>
                      <span className="font-mono">{downloadProgress}%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-primary/20">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-200"
                        style={{ width: `${downloadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : isInstalled ? (
                  <div className="flex items-center justify-between gap-2">
                    {isActive ? (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        <Check className="h-3.5 w-3.5" />
                        {t("settings.activeBadge")}
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setActiveModel(model.id)}
                        className="rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-colors shadow-2xs"
                      >
                        {t("settings.selectModelBtn")}
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => removeModel(model.id)}
                      title={t("settings.removeModelBtn")}
                      className="rounded-lg p-1.5 text-muted-foreground hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40 dark:hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => void downloadModel(model.id)}
                    className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold text-foreground hover:bg-muted transition-colors shadow-2xs"
                  >
                    <Download className="h-3.5 w-3.5 text-primary" />
                    {t("settings.downloadModelBtn")} ({model.sizeFormatted})
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
