import { create } from "zustand"
import {
  analyzeVoxCpmReference,
  createVoxCpmVoice,
  deleteVoxCpmVoice,
  fetchVoxCpmClonedVoices,
  fetchVoxCpmRuntime,
  generateVoxCpmSpeech,
  type VoxCpmGenerationResult,
} from "@/api/voxcpm"
import type {
  VoxCpmAnalysisResult,
  VoxCpmClonedVoice,
  VoxCpmRuntimeInfo,
} from "@/types/voxcpm"

/**
 * VoxCPM2 Studio store.
 *
 * Isolated from the VieNeu voice-lab store: no shared enrollment semantics.
 */
export type VoxCpmTabId = "clone" | "emotional" | "voices" | "runtime"

export interface VoxCpmState {
  activeTab: VoxCpmTabId
  runtime: VoxCpmRuntimeInfo | null
  isLoadingRuntime: boolean
  runtimeError: string | null
  clonedVoices: VoxCpmClonedVoice[]
  isLoadingVoices: boolean
  voicesError: string | null
  // Clone tab state (Phase 3)
  analysis: VoxCpmAnalysisResult | null
  isAnalyzing: boolean
  isCreatingVoice: boolean
  cloneError: string | null
  // Mock generation state (TTS cảm xúc tab)
  emotionPresetId: string
  customInstruction: string
  targetText: string
  selectedVoiceId: string | null
  // Phase 5 generation state
  isGenerating: boolean
  generation: VoxCpmGenerationResult | null
  generationError: string | null
  setActiveTab: (tab: VoxCpmTabId) => void
  loadRuntime: () => Promise<void>
  loadClonedVoices: () => Promise<void>
  analyzeReference: (file: File) => Promise<boolean>
  submitCloneVoice: (input: {
    file: File
    displayName: string
    consentGiven: boolean
    description?: string
    referenceTranscript?: string
  }) => Promise<boolean>
  removeVoice: (voiceId: string) => Promise<void>
  clearAnalysis: () => void
  setEmotionPreset: (presetId: string) => void
  setCustomInstruction: (instruction: string) => void
  setTargetText: (text: string) => void
  setSelectedVoiceId: (voiceId: string | null) => void
  generateEmotionalSpeech: () => Promise<boolean>
  clearGeneration: () => void
}

export const useVoxCpmStore = create<VoxCpmState>((set, get) => ({
  activeTab: "clone",
  runtime: null,
  isLoadingRuntime: false,
  runtimeError: null,
  clonedVoices: [],
  isLoadingVoices: false,
  voicesError: null,
  analysis: null,
  isAnalyzing: false,
  isCreatingVoice: false,
  cloneError: null,
  emotionPresetId: "neutral",
  customInstruction: "",
  targetText: "",
  selectedVoiceId: null,
  isGenerating: false,
  generation: null,
  generationError: null,
  setActiveTab: (tab) => set({ activeTab: tab }),
  loadRuntime: async () => {
    set({ isLoadingRuntime: true, runtimeError: null })
    try {
      const runtime = await fetchVoxCpmRuntime()
      set({ runtime, isLoadingRuntime: false })
    } catch (error) {
      set({
        isLoadingRuntime: false,
        runtimeError: error instanceof Error ? error.message : String(error),
      })
    }
  },
  loadClonedVoices: async () => {
    set({ isLoadingVoices: true, voicesError: null })
    try {
      const clonedVoices = await fetchVoxCpmClonedVoices()
      set({ clonedVoices, isLoadingVoices: false })
    } catch (error) {
      set({
        isLoadingVoices: false,
        voicesError: error instanceof Error ? error.message : String(error),
      })
    }
  },
  analyzeReference: async (file) => {
    set({ isAnalyzing: true, cloneError: null, analysis: null })
    try {
      const analysis = await analyzeVoxCpmReference(file)
      set({ analysis, isAnalyzing: false })
      return true
    } catch (error) {
      set({
        isAnalyzing: false,
        cloneError: error instanceof Error ? error.message : String(error),
      })
      return false
    }
  },
  submitCloneVoice: async (input) => {
    set({ isCreatingVoice: true, cloneError: null })
    try {
      const analysis = get().analysis
      await createVoxCpmVoice({
        file: input.file,
        displayName: input.displayName,
        consentGiven: input.consentGiven,
        description: input.description,
        referenceTranscript: input.referenceTranscript,
        selectedStartSeconds: analysis?.selected_start_seconds,
        selectedEndSeconds: analysis?.selected_end_seconds,
      })
      set({ isCreatingVoice: false, analysis: null })
      await get().loadClonedVoices()
      return true
    } catch (error) {
      set({
        isCreatingVoice: false,
        cloneError: error instanceof Error ? error.message : String(error),
      })
      return false
    }
  },
  removeVoice: async (voiceId) => {
    try {
      await deleteVoxCpmVoice(voiceId)
      set((state) => ({
        clonedVoices: state.clonedVoices.filter((voice) => voice.id !== voiceId),
        selectedVoiceId: state.selectedVoiceId === voiceId ? null : state.selectedVoiceId,
      }))
    } catch (error) {
      set({
        voicesError: error instanceof Error ? error.message : String(error),
      })
    }
  },
  clearAnalysis: () => set({ analysis: null, cloneError: null }),
  setEmotionPreset: (presetId) => set({ emotionPresetId: presetId }),
  setCustomInstruction: (instruction) => set({ customInstruction: instruction }),
  setTargetText: (text) => set({ targetText: text }),
  setSelectedVoiceId: (voiceId) => set({ selectedVoiceId: voiceId }),
  generateEmotionalSpeech: async () => {
    const { selectedVoiceId, targetText, emotionPresetId, customInstruction } = get()
    if (!selectedVoiceId || !targetText.trim()) return false
    set({ isGenerating: true, generationError: null, generation: null })
    try {
      const emotion = emotionPresetId === "custom" ? null : emotionPresetId
      const instruction = emotionPresetId === "custom" ? customInstruction : null
      const generation = await generateVoxCpmSpeech({
        voiceId: selectedVoiceId,
        text: targetText,
        emotion,
        instruction,
      })
      set({ isGenerating: false, generation })
      return true
    } catch (error) {
      set({
        isGenerating: false,
        generationError: error instanceof Error ? error.message : String(error),
      })
      return false
    }
  },
  clearGeneration: () => set({ generation: null, generationError: null }),
}))