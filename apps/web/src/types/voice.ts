export type Voice = {
  id: string
  languageCode: string
  languageShort: string
  voiceType: string
  displayName: string
  resourceId: string | null
  capturedAt: string | null
  providerId?: string | null
  gender?: string | null
  region?: string | null
  style?: string | null
  description?: string | null
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
  torch_available?: boolean
  torchaudio_available?: boolean
  clone_frontend_available?: boolean
  speaker_encoder_artifact_available?: boolean
  denoiser_artifact_available?: boolean
  reference_text_policy?: "ignored" | "optional" | "required"
  reference_text_used_for_enrollment?: boolean
  reference_min_seconds?: number
  reference_max_seconds?: number
  reason_code: string | null
  reason: string | null
}

export type VoiceAnalysis = {
  duration_seconds: number
  source_duration_seconds?: number | null
  reference_duration_seconds?: number | null
  selected_start_seconds: number
  selected_end_seconds: number
  speech_ratio: number
  noise_level_db: number
  clipping_ratio: number
  quality_score: number
  waveform_peaks: number[]
  warnings: string[]
  estimated_snr_db?: number | null
  noise_floor_dbfs?: number | null
  silence_ratio?: number | null
  level_stability?: number | null
  recommended_start_seconds?: number | null
  recommended_end_seconds?: number | null
  metrics?: {
    speech_score?: number
    noise_score?: number
    clipping_score?: number
    stability_score?: number
    segment_score?: number
  } | null
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
  source_duration_seconds?: number | null
  reference_duration_seconds?: number | null
  selected_start_seconds?: number | null
  selected_end_seconds?: number | null
  quality_score?: number | null
  consent_version: string
  profile_format_version?: string | null
  enrollment_artifact_path?: string | null
  cleaned_reference_audio_path?: string | null
  calibration_audio_path?: string | null
  engine_version?: string | null
  reference_fingerprint?: string | null
  denoise_mode?: "auto" | "off" | "on" | string | null
  denoise_applied?: boolean | null
  clone_mode?: "fidelity" | "stability" | string | null
  speaker_similarity_score?: number | null
  calibration_quality_score?: number | null
  calibration_available?: boolean | null
  enrollment_created_at?: string | null
}

export type VoiceListResponse = {
  items: Voice[]
  page: number
  pageSize: number
  total: number
}
