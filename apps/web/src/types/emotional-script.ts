export type DeliveryIntent =
  | "neutral"
  | "calm"
  | "joy"
  | "sad"
  | "fear"
  | "anger"
  | "surprise"
  | "tension"
  | "mysterious"
  | "narration"
  | "shout"
  | "whisper"

export type NonVerbalEvent = "laugh" | "sigh" | "clear_throat"

export type ScriptWarning = {
  code: string
  message: string
  value?: string | null
  line_id?: string | null
}

export type ScriptDocument = {
  version: number
  id?: string
  title: string
  revision: number
  source: { type: string; original_name?: string | null }
  defaults: {
    voice_id?: string | null
    global_delivery_prompt?: string | null
    base_rate: number
    pause_profile: "short" | "normal" | "long"
  }
  speakers: Array<{ id: string; name: string; voice_id?: string | null }>
  scenes: Array<{
    id: string
    title: string
    order: number
    lines: Array<{
      id: string
      order: number
      speaker_id?: string | null
      text: string
      delivery: {
        intent: DeliveryIntent
        intensity: number
        nonverbals: NonVerbalEvent[]
        pause_before_ms: number
        pause_after_ms: number
      }
      source_timing?: { start_ms: number; end_ms: number } | null
    }>
  }>
  warnings: ScriptWarning[]
}

export type ScriptParseResponse = {
  document: ScriptDocument
  line_count: number
  speaker_count: number
  warning_count: number
}

export type ScriptSummary = {
  id: string
  title: string
  revision: number
  schema_version: number
  document: ScriptDocument
  created_at: string
  updated_at: string
}

export type RenderSegment = {
  id: string
  line_id: string
  ordinal: number
  voice_id: string
  voice_mode: "PRESET" | "CLONE"
  status: "pending" | "queued" | "rendering" | "ready" | "failed" | "cancelled" | "reused"
  progress: number
  request_fingerprint: string
  audio_url?: string | null
  error_code?: string | null
  error_message?: string | null
}

export type ScriptRender = {
  id: string
  script_id: string
  script_revision: number
  status: "queued" | "planning" | "rendering" | "mixing" | "completed" | "partial_failed" | "failed" | "cancelled" | "interrupted"
  stage?: string | null
  progress: number
  total_segments: number
  cached_segments: number
  completed_segments: number
  failed_segments: number
  output_format: "mp3" | "wav"
  output_duration?: number | null
  output_file_size?: number | null
  output_url?: string | null
  error_code?: string | null
  error_message?: string | null
  segments: RenderSegment[]
}

