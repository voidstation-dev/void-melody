export type Voice = {
  id: string
  languageCode: string
  languageShort: string
  voiceType: string
  displayName: string
  resourceId: string
  capturedAt: string | null
}

export type VoiceCapabilities = {
  provider_id: string
  engine_id: string
  engine_version: string | null
  runtime_available: boolean
  device: string
  backend: string
  supports_preset_voices: boolean
  supports_voice_cloning: boolean
  supports_denoise: boolean
  supports_streaming: boolean
  reason_code: string | null
  reason: string | null
}

export type VoiceAnalysis = {
  duration_seconds: number
  selected_start_seconds: number
  selected_end_seconds: number
  speech_ratio: number
  noise_level_db: number
  clipping_ratio: number
  quality_score: number
  waveform_peaks: number[]
  warnings: string[]
}

export type CustomVoice = {
  id: string
  display_name: string
  transcript: string
  consent_given: boolean
  created_at: string
  updated_at?: string | null
  provider_id: string
  engine_id: string
  status: string
  duration_seconds?: number | null
  selected_start_seconds?: number | null
  selected_end_seconds?: number | null
  quality_score?: number | null
  consent_version: string
}

export type VoiceListResponse = {
  items: Voice[]
  page: number
  pageSize: number
  total: number
}
