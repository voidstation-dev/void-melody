/**
 * VoxCPM2 Studio types (Phase 1 — mock data only).
 *
 * VoxCPM2 is an isolated provider domain (provider_id = "voxcpm2").
 * These types must not reuse VieNeu voice/enrollment types.
 */

export const VOXCPM2_PROVIDER_ID = "voxcpm2"

export type VoxCpmRuntimeStatus =
  | "ready"
  | "not_installed"
  | "broken"
  | "downloading"

export type VoxCpmRuntimeInfo = {
  provider_id: string
  worker_running: boolean
  model_loaded: boolean
  device: string
  backend: "mock" | "real"
  sample_rate: number
  status: VoxCpmRuntimeStatus
  reason?: string | null
}

export type VoxCpmClonedVoice = {
  id: string
  display_name: string
  description?: string | null
  reference_duration_seconds: number
  sample_rate: number
  created_at: string
}

/** Result of POST /api/v1/voxcpm/voices/analyze (path-free summary). */
export type VoxCpmAnalysisResult = {
  duration_seconds: number
  source_duration_seconds: number
  selected_start_seconds: number
  selected_end_seconds: number
  reference_duration_seconds: number
  speech_ratio: number
  noise_level_db: number
  clipping_ratio: number
  quality_score: number
  waveform_peaks: number[]
  warnings: string[]
  recommended_start_seconds: number | null
  recommended_end_seconds: number | null
  metrics: Record<string, number> | null
}

export type VoxCpmEmotionPreset = {
  id: string
  label: string
  instruction: string
}

/** Phase 1 mock emotion presets — compiled to natural-language instructions in Phase 5. */
export const VOXCPM2_EMOTION_PRESETS: VoxCpmEmotionPreset[] = [
  { id: "neutral", label: "voxcpm.emotionNeutral", instruction: "Neutral, natural conversational delivery" },
  { id: "happy", label: "voxcpm.emotionHappy", instruction: "Happy, bright, upbeat energy" },
  { id: "excited", label: "voxcpm.emotionExcited", instruction: "Excited, enthusiastic, fast pace" },
  { id: "sad", label: "voxcpm.emotionSad", instruction: "Sad, restrained, speaking slowly, soft volume" },
  { id: "angry", label: "voxcpm.emotionAngry", instruction: "Angry, tense, forceful delivery" },
  { id: "fearful", label: "voxcpm.emotionFearful", instruction: "Fearful, trembling, hesitant" },
  { id: "gentle", label: "voxcpm.emotionGentle", instruction: "Gentle, warm, soothing tone" },
  { id: "whisper", label: "voxcpm.emotionWhisper", instruction: "Whispering, very soft, intimate" },
  { id: "calm", label: "voxcpm.emotionCalm", instruction: "Calm, steady, relaxed pace" },
  { id: "storytelling", label: "voxcpm.emotionStorytelling", instruction: "Narrative storytelling cadence, expressive pauses" },
  { id: "custom", label: "voxcpm.emotionCustom", instruction: "" },
]

/** Phase 1 mock cloned voices — replaced by real storage in Phase 3. */
export const VOXCPM2_MOCK_VOICES: VoxCpmClonedVoice[] = [
  {
    id: "voxcpm-mock-1",
    display_name: "Giọng demo Nam",
    description: null,
    reference_duration_seconds: 8.4,
    sample_rate: 48000,
    created_at: "2026-09-10T09:00:00Z",
  },
  {
    id: "voxcpm-mock-2",
    display_name: "Giọng demo Nữ",
    description: "Mẫu giọng nữ mềm mại",
    reference_duration_seconds: 6.1,
    sample_rate: 48000,
    created_at: "2026-09-10T09:05:00Z",
  },
]