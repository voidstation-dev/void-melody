import { apiFetch } from "@/lib/api-client"
import { CustomVoice, VoiceAnalysis } from "@/types/voice"

export async function analyzeVoiceSample(file: File): Promise<VoiceAnalysis> {
  const form = new FormData()
  form.append("audio_file", file)
  return apiFetch<VoiceAnalysis>("/api/v1/tts/voices/analyze", { method: "POST", body: form })
}

export async function cloneVoiceProfile({ file, displayName, consentGiven, analysis }: { file: File; displayName: string; consentGiven: boolean; analysis: VoiceAnalysis }): Promise<CustomVoice> {
  const form = new FormData()
  form.append("audio_file", file)
  form.append("transcript", "")
  form.append("display_name", displayName)
  form.append("consent_given", String(consentGiven))
  form.append("selected_start_seconds", String(analysis.selected_start_seconds))
  form.append("selected_end_seconds", String(analysis.selected_end_seconds))
  return apiFetch<CustomVoice>("/api/v1/tts/voices/clone", { method: "POST", body: form })
}
