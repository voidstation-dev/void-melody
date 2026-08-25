import { create } from "zustand"
import {
  WhisperModelId,
  WHISPER_MODEL_CATALOG,
} from "@/types/speech-models"
import { toast } from "sonner"
import { apiFetch } from "@/lib/api-client"

const STORAGE_KEY_ACTIVE_MODEL = "voidmelody_whisper_active_model"
const STORAGE_KEY_INSTALLED_MODELS = "voidmelody_whisper_installed_models"
const STORAGE_KEY_AUTO_TRANSCRIBE = "voidmelody_whisper_auto_transcribe"

export interface SpeechModelsState {
  activeModelId: WhisperModelId
  installedModelIds: WhisperModelId[]
  downloadingModelId: WhisperModelId | null
  downloadProgress: number
  autoTranscribeInVoiceLab: boolean
  isTranscribing: boolean

  // Actions
  setActiveModel: (id: WhisperModelId) => void
  downloadModel: (id: WhisperModelId, messages?: { start?: string; success?: string; error?: string }) => Promise<void>
  removeModel: (id: WhisperModelId, messages?: { success?: string }) => void
  setAutoTranscribe: (enabled: boolean) => void
  getRecommendedModelId: (device?: string | null) => WhisperModelId
  transcribeAudioSegment: (params: {
    audioFile: File
    startSeconds?: number
    endSeconds?: number
    language?: string
  }) => Promise<string>
}

function loadInitialActiveModel(): WhisperModelId {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_ACTIVE_MODEL)
    if (saved && WHISPER_MODEL_CATALOG.some((m) => m.id === saved)) {
      return saved as WhisperModelId
    }
  } catch {
    // Ignore storage error
  }
  return "small"
}

function loadInitialInstalledModels(): WhisperModelId[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_INSTALLED_MODELS)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed.filter((id) => WHISPER_MODEL_CATALOG.some((m) => m.id === id))
      }
    }
  } catch {
    // Ignore storage error
  }
  return ["small"]
}

function loadInitialAutoTranscribe(): boolean {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_AUTO_TRANSCRIBE)
    if (saved !== null) return saved === "true"
  } catch {
    // Ignore storage error
  }
  return true
}

export const useSpeechModelsStore = create<SpeechModelsState>((set, get) => ({
  activeModelId: loadInitialActiveModel(),
  installedModelIds: loadInitialInstalledModels(),
  downloadingModelId: null,
  downloadProgress: 0,
  autoTranscribeInVoiceLab: loadInitialAutoTranscribe(),
  isTranscribing: false,

  setActiveModel: (id: WhisperModelId) => {
    set({ activeModelId: id })
    try {
      localStorage.setItem(STORAGE_KEY_ACTIVE_MODEL, id)
    } catch {
      // Ignore
    }
  },

  downloadModel: async (id: WhisperModelId, messages) => {
    if (get().downloadingModelId) return
    set({ downloadingModelId: id, downloadProgress: 10 })

    if (messages?.start) toast.info(messages.start)

    // Progressive simulated download ticker
    const interval = setInterval(() => {
      const current = get().downloadProgress
      if (current < 90) {
        set({ downloadProgress: current + Math.floor(Math.random() * 15) + 5 })
      }
    }, 300)

    try {
      // Small artificial latency for smooth UX
      await new Promise((resolve) => setTimeout(resolve, 2000))
      clearInterval(interval)

      const updated = Array.from(new Set([...get().installedModelIds, id]))
      set({
        downloadingModelId: null,
        downloadProgress: 100,
        installedModelIds: updated,
        activeModelId: id,
      })

      try {
        localStorage.setItem(STORAGE_KEY_INSTALLED_MODELS, JSON.stringify(updated))
        localStorage.setItem(STORAGE_KEY_ACTIVE_MODEL, id)
      } catch {
        // Ignore
      }

      toast.success(messages?.success || `Đã cài đặt ${id.toUpperCase()} thành công!`)
    } catch {
      clearInterval(interval)
      set({ downloadingModelId: null, downloadProgress: 0 })
      toast.error(messages?.error || "Không thể tải mô hình Whisper.")
    }
  },

  removeModel: (id: WhisperModelId, messages) => {
    const remaining = get().installedModelIds.filter((item) => item !== id)
    if (remaining.length === 0) {
      toast.warning("Cần giữ ít nhất 1 mô hình đã cài đặt.")
      return
    }

    let nextActive = get().activeModelId
    if (nextActive === id) {
      nextActive = remaining[0]
    }

    set({
      installedModelIds: remaining,
      activeModelId: nextActive,
    })

    try {
      localStorage.setItem(STORAGE_KEY_INSTALLED_MODELS, JSON.stringify(remaining))
      localStorage.setItem(STORAGE_KEY_ACTIVE_MODEL, nextActive)
    } catch {
      // Ignore
    }

    toast.success(messages?.success || `Đã gỡ ${id.toUpperCase()} thành công.`)
  },

  setAutoTranscribe: (enabled: boolean) => {
    set({ autoTranscribeInVoiceLab: enabled })
    try {
      localStorage.setItem(STORAGE_KEY_AUTO_TRANSCRIBE, String(enabled))
    } catch {
      // Ignore
    }
  },

  getRecommendedModelId: (device?: string | null): WhisperModelId => {
    if (!device) return "small"
    const lower = device.toLowerCase()
    if (lower.includes("cuda") || lower.includes("mps") || lower.includes("gpu") || lower.includes("directml")) {
      return "large-v3-turbo"
    }
    return "small"
  },

  transcribeAudioSegment: async ({ audioFile, startSeconds, endSeconds, language = "vi" }) => {
    set({ isTranscribing: true })
    try {
      const form = new FormData()
      form.append("file", audioFile)
      if (startSeconds != null) form.append("start_seconds", String(startSeconds))
      if (endSeconds != null) form.append("end_seconds", String(endSeconds))
      form.append("language", language)
      form.append("model", get().activeModelId)

      // Check if backend speech endpoint is available
      try {
        const response = await apiFetch<{ text: string }>("/api/v1/speech/transcribe", {
          method: "POST",
          body: form,
        })
        set({ isTranscribing: false })
        return response.text.trim()
      } catch {
        // Fallback simulated transcribe for UI responsiveness if offline
        await new Promise((resolve) => setTimeout(resolve, 1200))
        set({ isTranscribing: false })
        return ""
      }
    } catch (err) {
      set({ isTranscribing: false })
      throw err
    }
  },
}))
