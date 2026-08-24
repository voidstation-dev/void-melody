import { apiFetch } from "@/lib/api-client"
import { CustomVoice, VoiceAnalysis } from "@/types/voice"

export async function analyzeVoiceSample(file: File): Promise<VoiceAnalysis> {
  const form = new FormData()
  form.append("audio_file", file)
  return apiFetch<VoiceAnalysis>("/api/v1/tts/voices/analyze", { method: "POST", body: form })
}

export async function cloneVoiceProfile({
  file,
  displayName,
  consentGiven,
  analysis,
  startSeconds,
  endSeconds,
  denoiseMode = "auto",
  cloneMode = "fidelity",
}: {
  file: File
  displayName: string
  consentGiven: boolean
  analysis?: VoiceAnalysis | null
  startSeconds?: number | null
  endSeconds?: number | null
  denoiseMode?: "auto" | "off" | "on" | string
  cloneMode?: "fidelity" | "stability" | string
}): Promise<CustomVoice> {
  const form = new FormData()
  form.append("audio_file", file)
  form.append("transcript", "")
  form.append("display_name", displayName)
  form.append("consent_given", String(consentGiven))
  
  const start = startSeconds ?? analysis?.selected_start_seconds ?? 0
  const end = endSeconds ?? analysis?.selected_end_seconds ?? analysis?.duration_seconds ?? 6
  
  form.append("selected_start_seconds", String(start))
  form.append("selected_end_seconds", String(end))
  form.append("denoise_mode", denoiseMode)
  form.append("clone_mode", cloneMode)
  
  return apiFetch<CustomVoice>("/api/v1/tts/voices/clone", { method: "POST", body: form })
}

export function getVoiceCalibrationAudioUrl(voiceId: string): string {
  return `/api/v1/tts/voices/custom/${voiceId}/calibration/audio`
}
