export type DeliveryTagType = "native" | "emotion" | "delivery"

export type DeliveryTag = {
  id: string
  label: string
  type: DeliveryTagType
  token: string
  icon?: string
  engine?: string[]
  description?: string
  colorVariant?: "green" | "amber" | "blue" | "purple"
}

export type CueItem = {
  type: DeliveryTagType
  value: string
  rawToken: string
}

export type ScriptSegment = {
  id: string
  text: string
  cleanText: string
  cues: CueItem[]
}

export type ScriptAnalysisResult = {
  rawText: string
  segments: ScriptSegment[]
  characterCount: number
  wordCount: number
  nativeCueCount: number
  emotionCount: number
  deliveryCount: number
  totalCueCount: number
  unsupportedCues: string[]
  estimatedJobs: number
}

export type PreflightCheckSeverity = "success" | "warning" | "error" | "info"

export type PreflightCheck = {
  id: string
  severity: PreflightCheckSeverity
  message: string
  detail?: string
}

export type PreflightReport = {
  isValid: boolean
  canGenerate: boolean
  checks: PreflightCheck[]
  stats: {
    segmentCount: number
    characterCount: number
    nativeCueCount: number
    emotionCount: number
    estimatedJobs: number
  }
}

export type AudioStudioDraft = {
  text: string
  selectedVoiceId: string
  speed: number
  format: "mp3" | "wav"
  updatedAt: number
}
