import { create } from "zustand"
import { analyzeVoiceSample, cloneVoiceProfile } from "@/lib/voice-lab-api"
import type { CustomVoice, VoiceAnalysis } from "@/types/voice"
import {
  ACCEPTED_AUDIO_EXTENSIONS,
  ACCEPTED_AUDIO_MIME_TYPES,
  MAX_VOICE_SAMPLE_BYTES,
} from "@/constants"
import type { QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

export interface VoiceLabStageMessages {
  upload: string
  analyze: string
  extract: string
  saving: string
  completed: string
  successToast: string
  errorToast: string
}

export interface VoiceLabFileErrorMessages {
  formatError: string
  sizeError: string
}

export interface VoiceLabState {
  // Input file & validation
  file: File | null
  fileUrl: string | null
  fileError: string | null

  // Configuration
  voiceName: string
  consent: boolean
  selectedSegment: { start: number; end: number } | null
  denoiseMode: "auto" | "off" | "on"
  cloneMode: "fidelity" | "stability"
  referenceTranscript: string
  transcriptSegmentKey: string | null
  transcriptNeedsReview: boolean

  // Analysis state
  analysis: VoiceAnalysis | null
  isAnalyzing: boolean
  analysisError: string | null

  // Clone lifecycle & progress
  isCloning: boolean
  cloneProgress: number
  cloneStage: string
  cloneError: string | null
  createdProfile: CustomVoice | null

  // Preview state
  previewText: string
  previewRate: string
  previewJobId: string | null
  previewError: string | null

  // Internal timer references
  _cloneTimerIds: ReturnType<typeof setTimeout>[]

  // Actions
  selectFile: (file: File | null | undefined, errorMessages?: VoiceLabFileErrorMessages) => void
  setFileError: (error: string | null) => void
  setVoiceName: (name: string) => void
  setConsent: (consent: boolean) => void
  setSelectedSegment: (segment: { start: number; end: number } | null) => void
  setDenoiseMode: (mode: "auto" | "off" | "on") => void
  setCloneMode: (mode: "fidelity" | "stability") => void
  setReferenceTranscript: (transcript: string) => void
  setTranscriptSegmentKey: (key: string | null) => void
  setTranscriptNeedsReview: (needsReview: boolean) => void
  setPreviewText: (text: string) => void
  setPreviewRate: (rate: string) => void
  setPreviewJobId: (jobId: string | null) => void
  setPreviewError: (error: string | null) => void

  startAnalysis: (file: File) => Promise<void>
  startClone: (options: {
    queryClient: QueryClient
    stages: VoiceLabStageMessages
  }) => Promise<CustomVoice | null>
  reset: () => void
}

export const useVoiceLabStore = create<VoiceLabState>((set, get) => ({
  file: null,
  fileUrl: null,
  fileError: null,

  voiceName: "",
  consent: false,
  selectedSegment: null,
  denoiseMode: "auto",
  cloneMode: "fidelity",
  referenceTranscript: "",
  transcriptSegmentKey: null,
  transcriptNeedsReview: false,

  analysis: null,
  isAnalyzing: false,
  analysisError: null,

  isCloning: false,
  cloneProgress: 0,
  cloneStage: "",
  cloneError: null,
  createdProfile: null,

  previewText: "",
  previewRate: "1",
  previewJobId: null,
  previewError: null,

  _cloneTimerIds: [],

  selectFile: (nextFile, errorMessages) => {
    const currentUrl = get().fileUrl
    if (currentUrl && typeof URL.revokeObjectURL === "function") {
      URL.revokeObjectURL(currentUrl)
    }

    if (!nextFile) {
      set({
        file: null,
        fileUrl: null,
        fileError: null,
        analysis: null,
        selectedSegment: null,
        createdProfile: null,
        cloneError: null,
      })
      return
    }

    const extension = `.${nextFile.name.split(".").pop()?.toLowerCase()}`
    const isExtensionValid = (ACCEPTED_AUDIO_EXTENSIONS as readonly string[]).includes(extension)
    const isMimeValid =
      !nextFile.type || (ACCEPTED_AUDIO_MIME_TYPES as readonly string[]).includes(nextFile.type)

    if (!isExtensionValid || !isMimeValid) {
      set({
        file: null,
        fileUrl: null,
        fileError: errorMessages?.formatError || "Unsupported audio format.",
        analysis: null,
        createdProfile: null,
      })
      return
    }

    if (nextFile.size > MAX_VOICE_SAMPLE_BYTES) {
      set({
        file: null,
        fileUrl: null,
        fileError: errorMessages?.sizeError || "File size too large.",
        analysis: null,
        createdProfile: null,
      })
      return
    }

    const newUrl =
      typeof URL.createObjectURL === "function" ? URL.createObjectURL(nextFile) : null

    set({
      file: nextFile,
      fileUrl: newUrl,
      fileError: null,
      selectedSegment: null,
      analysis: null,
      createdProfile: null,
      cloneProgress: 0,
      cloneStage: "",
      cloneError: null,
    })

    get().startAnalysis(nextFile)
  },

  setFileError: (error) => set({ fileError: error }),
  setVoiceName: (voiceName) => set({ voiceName }),
  setConsent: (consent) => set({ consent }),
  setSelectedSegment: (selectedSegment) => set({ selectedSegment }),
  setDenoiseMode: (denoiseMode) => set({ denoiseMode }),
  setCloneMode: (cloneMode) => set({ cloneMode }),
  setReferenceTranscript: (referenceTranscript) => set({ referenceTranscript }),
  setTranscriptSegmentKey: (transcriptSegmentKey) => set({ transcriptSegmentKey }),
  setTranscriptNeedsReview: (transcriptNeedsReview) => set({ transcriptNeedsReview }),
  setPreviewText: (previewText) => set({ previewText }),
  setPreviewRate: (previewRate) => set({ previewRate }),
  setPreviewJobId: (previewJobId) => set({ previewJobId }),
  setPreviewError: (previewError) => set({ previewError }),

  startAnalysis: async (file: File) => {
    set({ isAnalyzing: true, analysisError: null })
    try {
      const analysis = await analyzeVoiceSample(file)
      set({ analysis, isAnalyzing: false })
    } catch (err: any) {
      set({
        analysis: null,
        isAnalyzing: false,
        analysisError: err?.message || "Failed to analyze audio sample.",
      })
    }
  },

  startClone: async ({ queryClient, stages }) => {
    const state = get()
    if (!state.file || !state.voiceName.trim() || state.isCloning) return null

    // Clear existing timers
    state._cloneTimerIds.forEach(clearTimeout)

    set({
      isCloning: true,
      cloneProgress: 15,
      cloneStage: stages.upload,
      cloneError: null,
      _cloneTimerIds: [],
    })

    const t1 = setTimeout(() => {
      set({ cloneProgress: 40, cloneStage: stages.analyze })
    }, 600)

    const t2 = setTimeout(() => {
      set({ cloneProgress: 75, cloneStage: stages.extract })
    }, 1800)

    const t3 = setTimeout(() => {
      set({ cloneProgress: 92, cloneStage: stages.saving })
    }, 3200)

    set({ _cloneTimerIds: [t1, t2, t3] })

    const startSeconds =
      state.selectedSegment?.start ?? state.analysis?.selected_start_seconds ?? 0
    const endSeconds =
      state.selectedSegment?.end ??
      state.analysis?.selected_end_seconds ??
      state.analysis?.duration_seconds ??
      6

    try {
      const profile = await cloneVoiceProfile({
        file: state.file,
        displayName: state.voiceName.trim(),
        transcript: state.referenceTranscript,
        consentGiven: state.consent,
        analysis: state.analysis,
        startSeconds,
        endSeconds,
        denoiseMode: state.denoiseMode,
        cloneMode: state.cloneMode,
      })

      // Clear progression timers
      get()._cloneTimerIds.forEach(clearTimeout)

      set({
        isCloning: false,
        cloneProgress: 100,
        cloneStage: stages.completed,
        createdProfile: profile,
        _cloneTimerIds: [],
      })

      await queryClient.invalidateQueries({ queryKey: ["custom-voices"] })
      toast.success(stages.successToast)
      return profile
    } catch (error: any) {
      get()._cloneTimerIds.forEach(clearTimeout)
      const message = error?.message || stages.errorToast
      set({
        isCloning: false,
        cloneProgress: 0,
        cloneStage: "",
        cloneError: message,
        _cloneTimerIds: [],
      })
      toast.error(message)
      return null
    }
  },

  reset: () => {
    const currentUrl = get().fileUrl
    if (currentUrl && typeof URL.revokeObjectURL === "function") {
      URL.revokeObjectURL(currentUrl)
    }
    get()._cloneTimerIds.forEach(clearTimeout)

    set({
      file: null,
      fileUrl: null,
      fileError: null,
      voiceName: "",
      consent: false,
      selectedSegment: null,
      denoiseMode: "auto",
      cloneMode: "fidelity",
      referenceTranscript: "",
      transcriptSegmentKey: null,
      transcriptNeedsReview: false,
      analysis: null,
      isAnalyzing: false,
      analysisError: null,
      isCloning: false,
      cloneProgress: 0,
      cloneStage: "",
      cloneError: null,
      createdProfile: null,
      previewText: "",
      previewRate: "1",
      previewJobId: null,
      previewError: null,
      _cloneTimerIds: [],
    })
  },
}))
