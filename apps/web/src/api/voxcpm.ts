/**
 * VoxCPM2 API client.
 *
 * Isolated provider domain (provider_id = "voxcpm2"): these endpoints never
 * touch VieNeu / tts_custom_voices. Clone voices live under /api/v1/voxcpm/*.
 */
import { apiFetch, resolveApiUrl } from "@/lib/api-client"
import type {
  VoxCpmAnalysisResult,
  VoxCpmClonedVoice,
  VoxCpmRuntimeInfo,
} from "@/types/voxcpm"
import { VOXCPM2_MOCK_VOICES } from "@/types/voxcpm"

const MOCK_RUNTIME: VoxCpmRuntimeInfo = {
  provider_id: "voxcpm2",
  worker_running: true,
  model_loaded: false,
  device: "cpu",
  backend: "mock",
  sample_rate: 48000,
  status: "ready",
  reason: null,
}

export async function fetchVoxCpmRuntime(): Promise<VoxCpmRuntimeInfo> {
  try {
    const state = await apiFetch<{
      provider_id: string
      env_present: boolean
      package_installed: boolean
      model_downloaded: boolean
      downloaded_bytes: number
    }>("/api/v1/voxcpm/runtime-state")
    const status: VoxCpmRuntimeInfo["status"] = state.package_installed
      ? "ready"
      : "not_installed"
    return {
      provider_id: state.provider_id,
      worker_running: state.package_installed,
      model_loaded: false, // live model state comes from the worker runtime_info RPC on demand
      device: "auto",
      backend: "real",
      sample_rate: 48000,
      status,
      reason: state.package_installed
        ? null
        : state.model_downloaded
          ? "runtime-missing"
          : "not-installed",
    }
  } catch {
    // No backend yet — fall back to the Phase 1 demo state so the UI stays usable.
    return MOCK_RUNTIME
  }
}

// ---- Phase 10: Settings (installation lifecycle) ----

export type VoxCpmInstallationInfo = {
  provider_id: string
  model_id: string
  env_present: boolean
  package_installed: boolean
  model_status: "downloaded" | "not_downloaded"
  model_snapshot: string | null
  downloaded_bytes: number
  storage_dir: string
  sample_rate: number
  device_policy: string
}

export type VoxCpmDownloadProgress = {
  provider_id: string
  model_id: string
  downloaded_bytes: number
  expected_bytes: number
  complete: boolean
}

export async function fetchVoxCpmInstallation(): Promise<VoxCpmInstallationInfo> {
  return apiFetch<VoxCpmInstallationInfo>("/api/v1/voxcpm/installation")
}

export async function fetchVoxCpmDownloadProgress(): Promise<VoxCpmDownloadProgress> {
  return apiFetch<VoxCpmDownloadProgress>(
    "/api/v1/voxcpm/installation/download-progress",
  )
}

export async function installVoxCpmRuntime(): Promise<void> {
  await apiFetch<void>("/api/v1/voxcpm/installation/install", { method: "POST" })
}

export async function verifyVoxCpmInstallation(): Promise<{ ok: boolean; version: string | null; error: string | null }> {
  return apiFetch("/api/v1/voxcpm/installation/verify", { method: "POST" })
}

export async function removeVoxCpmEnv(): Promise<void> {
  await apiFetch<void>("/api/v1/voxcpm/installation/env", { method: "DELETE" })
}

export async function removeVoxCpmModel(): Promise<void> {
  await apiFetch<void>("/api/v1/voxcpm/installation/model", { method: "DELETE" })
}

export async function fetchVoxCpmClonedVoices(): Promise<VoxCpmClonedVoice[]> {
  try {
    const response = await apiFetch<{ items: VoxCpmClonedVoice[]; total: number }>(
      "/api/v1/voxcpm/voices",
    )
    return response.items
  } catch {
    // No backend yet — fall back to the Phase 1 demo data so the UI stays usable.
    return VOXCPM2_MOCK_VOICES
  }
}

export async function analyzeVoxCpmReference(
  file: File,
): Promise<VoxCpmAnalysisResult> {
  const form = new FormData()
  form.append("audio_file", file, file.name)
  return apiFetch<VoxCpmAnalysisResult>("/api/v1/voxcpm/voices/analyze", {
    method: "POST",
    body: form,
  })
}

export async function createVoxCpmVoice(input: {
  file: File
  displayName: string
  consentGiven: boolean
  description?: string
  referenceTranscript?: string
  selectedStartSeconds?: number
  selectedEndSeconds?: number
}): Promise<VoxCpmClonedVoice> {
  const form = new FormData()
  form.append("audio_file", input.file, input.file.name)
  form.append("display_name", input.displayName)
  form.append("consent_given", String(input.consentGiven))
  if (input.description) form.append("description", input.description)
  if (input.referenceTranscript)
    form.append("reference_transcript", input.referenceTranscript)
  if (input.selectedStartSeconds !== undefined)
    form.append("selected_start_seconds", String(input.selectedStartSeconds))
  if (input.selectedEndSeconds !== undefined)
    form.append("selected_end_seconds", String(input.selectedEndSeconds))
  return apiFetch<VoxCpmClonedVoice>("/api/v1/voxcpm/voices", {
    method: "POST",
    body: form,
  })
}

export async function deleteVoxCpmVoice(voiceId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/voxcpm/voices/${voiceId}`, { method: "DELETE" })
}

export function resolveVoxCpmReferenceAudioUrl(voiceId: string): string {
  return resolveApiUrl(`/api/v1/voxcpm/voices/${voiceId}/reference/audio`)
}

// ---- Phase 5: emotional generation ----

export type VoxCpmGenerationResult = {
  audio_url: string
  output_path: string
  sample_rate: number
  duration_seconds: number
  method: string
  instruction: string | null
  voice_id: string
  emotion: string | null
}

export async function generateVoxCpmSpeech(input: {
  voiceId: string
  text: string
  emotion?: string | null
  instruction?: string | null
  cfgValue?: number
  inferenceTimesteps?: number
  seed?: number | null
}): Promise<VoxCpmGenerationResult> {
  return apiFetch<VoxCpmGenerationResult>("/api/v1/voxcpm/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      voice_id: input.voiceId,
      text: input.text,
      emotion: input.emotion ?? null,
      instruction: input.instruction ?? null,
      cfg_value: input.cfgValue ?? 2.0,
      inference_timesteps: input.inferenceTimesteps ?? 10,
      seed: input.seed ?? null,
    }),
  })
}

export function resolveVoxCpmGenerationAudioUrl(generationId: string): string {
  // audio_url is like /api/v1/voxcpm/generations/<stem>
  return resolveApiUrl(generationId)
}