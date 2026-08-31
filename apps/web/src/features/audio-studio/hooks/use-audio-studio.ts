import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useVoices } from "@/hooks/use-voices"
import { useCustomVoices } from "@/hooks/use-custom-voices"
import { insertTagAtCursor, parseScript } from "../lib/script-parser"
import { evaluatePreflight } from "../lib/preflight"
import type { AudioStudioDraft, PreflightReport, ScriptAnalysisResult } from "../types"

const DRAFT_STORAGE_KEY = "voidmelody_audio_studio_draft_v1"

function getInitialDraft(): Partial<AudioStudioDraft> {
  if (typeof window === "undefined") return {}
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY)
    if (raw) return JSON.parse(raw) as AudioStudioDraft
  } catch {
    // ignore
  }
  return {}
}

export function useAudioStudio(initialVoiceId?: string) {
  const [text, setText] = useState<string>(() => getInitialDraft().text || "")
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>(
    () => initialVoiceId || getInitialDraft().selectedVoiceId || "",
  )
  const [speed, setSpeed] = useState<number>(() => getInitialDraft().speed || 1.0)
  const [outputFormat, setOutputFormat] = useState<"mp3" | "wav">(
    () => getInitialDraft().format || "mp3",
  )
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(
    () => getInitialDraft().updatedAt || null,
  )

  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // Fetch voices catalogs
  const { data: presetData, isLoading: isLoadingPresets } = useVoices()
  const { data: customData, isLoading: isLoadingCustom } = useCustomVoices(undefined, 1, 100)

  const allVoices = useMemo(() => {
    const presets = presetData?.items ?? []
    const customs = (customData?.items ?? []).map((cv) => ({
      id: cv.id,
      voiceType: cv.id,
      displayName: cv.display_name,
      languageCode: "vi-VN",
      languageShort: "vi",
      resourceId: "",
      capturedAt: null,
      providerId: cv.provider_id || "vieneu",
    }))
    return [...presets, ...customs]
  }, [presetData?.items, customData?.items])

  const selectedVoice = useMemo(() => {
    if (!allVoices.length) return undefined
    if (selectedVoiceId) {
      const match = allVoices.find((v) => v.voiceType === selectedVoiceId || v.id === selectedVoiceId)
      if (match) return match
    }
    return allVoices.find((v) => v.providerId === "vieneu") || allVoices[0]
  }, [allVoices, selectedVoiceId])

  const effectiveVoiceId = selectedVoice?.voiceType || selectedVoice?.id || ""

  useEffect(() => {
    if (
      effectiveVoiceId &&
      selectedVoiceId !== effectiveVoiceId &&
      !allVoices.some((v) => v.voiceType === selectedVoiceId || v.id === selectedVoiceId)
    ) {
      setSelectedVoiceId(effectiveVoiceId)
    }
  }, [effectiveVoiceId, selectedVoiceId, allVoices])

  // Autosave draft debounce
  useEffect(() => {
    if (!text.trim()) return
    const timer = setTimeout(() => {
      try {
        const draft: AudioStudioDraft = {
          text,
          selectedVoiceId: effectiveVoiceId,
          speed,
          format: outputFormat,
          updatedAt: Date.now(),
        }
        localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft))
        setLastSavedAt(draft.updatedAt)
      } catch {
        // ignore
      }
    }, 1500)
    return () => clearTimeout(timer)
  }, [text, effectiveVoiceId, speed, outputFormat])

  const selectedVoiceProvider = selectedVoice?.providerId || "vieneu"

  // Real-time reactive analysis
  const analysis: ScriptAnalysisResult = useMemo(
    () => parseScript(text, selectedVoiceProvider),
    [text, selectedVoiceProvider],
  )

  // Real-time reactive preflight report
  const preflight: PreflightReport = useMemo(
    () => evaluatePreflight(analysis, effectiveVoiceId, selectedVoiceProvider, selectedVoice?.displayName),
    [analysis, effectiveVoiceId, selectedVoiceProvider, selectedVoice?.displayName],
  )

  // Insert tag token into textarea at current cursor position
  const insertTag = useCallback((token: string) => {
    const textarea = textareaRef.current
    if (!textarea) {
      setText((prev) => (prev ? `${prev} ${token}` : token))
      return
    }

    const start = textarea.selectionStart ?? text.length
    const end = textarea.selectionEnd ?? text.length

    const { nextText, nextCursorPos } = insertTagAtCursor(text, token, start, end)
    setText(nextText)

    requestAnimationFrame(() => {
      textarea.focus()
      textarea.setSelectionRange(nextCursorPos, nextCursorPos)
    })
  }, [text])

  const clearText = useCallback(() => {
    setText("")
    localStorage.removeItem(DRAFT_STORAGE_KEY)
    setLastSavedAt(null)
  }, [])

  return {
    text,
    setText,
    selectedVoiceId: effectiveVoiceId,
    setSelectedVoiceId,
    selectedVoice,
    allVoices,
    isLoadingVoices: isLoadingPresets || isLoadingCustom,
    speed,
    setSpeed,
    outputFormat,
    setOutputFormat,
    lastSavedAt,
    textareaRef,
    analysis,
    preflight,
    insertTag,
    clearText,
  }
}
