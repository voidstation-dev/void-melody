export type WhisperModelId =
  | "tiny"
  | "base"
  | "small"
  | "medium"
  | "large-v3-turbo"

export type SpeedTier = "ultra-fast" | "fast" | "standard" | "heavy"
export type HardwareRecommendation = "cpu" | "gpu" | "low-end" | null
export type ModelInstallStatus = "not_installed" | "downloading" | "ready" | "error"

export interface WhisperModelMetadata {
  id: WhisperModelId
  name: string
  version: string
  sizeBytes: number
  sizeFormatted: string
  minRamGb: number
  recommendedDevice: "cpu" | "gpu" | "any"
  vietnameseAccuracy: number // 0-100 percentage
  speedTier: SpeedTier
  hardwareRecommendation: HardwareRecommendation
  descriptionKey: string
}

export const WHISPER_MODEL_CATALOG: readonly WhisperModelMetadata[] = [
  {
    id: "tiny",
    name: "Whisper Tiny",
    version: "v1.0",
    sizeBytes: 75 * 1024 * 1024,
    sizeFormatted: "75 MB",
    minRamGb: 1,
    recommendedDevice: "any",
    vietnameseAccuracy: 65,
    speedTier: "ultra-fast",
    hardwareRecommendation: "low-end",
    descriptionKey: "settings.speechModelTinyDesc",
  },
  {
    id: "base",
    name: "Whisper Base",
    version: "v1.0",
    sizeBytes: 145 * 1024 * 1024,
    sizeFormatted: "145 MB",
    minRamGb: 2,
    recommendedDevice: "cpu",
    vietnameseAccuracy: 80,
    speedTier: "fast",
    hardwareRecommendation: null,
    descriptionKey: "settings.speechModelBaseDesc",
  },
  {
    id: "small",
    name: "Whisper Small",
    version: "v1.0",
    sizeBytes: 480 * 1024 * 1024,
    sizeFormatted: "480 MB",
    minRamGb: 4,
    recommendedDevice: "cpu",
    vietnameseAccuracy: 92,
    speedTier: "standard",
    hardwareRecommendation: "cpu",
    descriptionKey: "settings.speechModelSmallDesc",
  },
  {
    id: "medium",
    name: "Whisper Medium",
    version: "v1.0",
    sizeBytes: 1500 * 1024 * 1024,
    sizeFormatted: "1.5 GB",
    minRamGb: 8,
    recommendedDevice: "any",
    vietnameseAccuracy: 96,
    speedTier: "standard",
    hardwareRecommendation: null,
    descriptionKey: "settings.speechModelMediumDesc",
  },
  {
    id: "large-v3-turbo",
    name: "Whisper Large-v3 Turbo",
    version: "v3.0",
    sizeBytes: 1600 * 1024 * 1024,
    sizeFormatted: "1.6 GB",
    minRamGb: 6,
    recommendedDevice: "gpu",
    vietnameseAccuracy: 99,
    speedTier: "fast",
    hardwareRecommendation: "gpu",
    descriptionKey: "settings.speechModelLargeTurboDesc",
  },
] as const
