"use client"

import { useCallback, useEffect, useState } from "react"
import { apiFetchBlob } from "@/lib/api-client"

type PreviewStatus = "idle" | "loading" | "playing" | "error"

type PreviewSnapshot = {
  voiceId: string | null
  status: PreviewStatus
  error: string | null
}

const listeners = new Set<() => void>()
const cachedUrls = new Map<string, string>()
let snapshot: PreviewSnapshot = { voiceId: null, status: "idle", error: null }
let activeAudio: HTMLAudioElement | null = null
let activeRequest = 0
let mountedConsumers = 0

function emit() {
  listeners.forEach((listener) => listener())
}

function setSnapshot(next: PreviewSnapshot) {
  snapshot = next
  emit()
}

function releaseActiveAudio() {
  if (activeAudio) {
    activeAudio.pause()
    activeAudio.onended = null
    activeAudio.onpause = null
    activeAudio.onerror = null
  }
  activeAudio = null
}

function clearPreviewCache() {
  activeRequest += 1
  releaseActiveAudio()
  cachedUrls.forEach((url) => {
    if (typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(url)
  })
  cachedUrls.clear()
  snapshot = { voiceId: null, status: "idle", error: null }
}

function createAudio(url: string, voiceId: string) {
  const audio = new Audio(url)
  audio.onended = () => {
    if (snapshot.voiceId === voiceId) setSnapshot({ voiceId, status: "idle", error: null })
  }
  audio.onpause = () => {
    if (snapshot.voiceId === voiceId && snapshot.status === "playing") {
      setSnapshot({ voiceId, status: "idle", error: null })
    }
  }
  audio.onerror = () => {
    if (snapshot.voiceId === voiceId) {
      setSnapshot({ voiceId, status: "error", error: "playback" })
    }
  }
  return audio
}

export function useVoicePreview(voiceId?: string) {
  const [, setVersion] = useState(0)
  const forceUpdate = useCallback(() => setVersion((version) => version + 1), [])

  useEffect(() => {
    mountedConsumers += 1
    listeners.add(forceUpdate)
    return () => {
      mountedConsumers -= 1
      listeners.delete(forceUpdate)
      if (mountedConsumers === 0) clearPreviewCache()
    }
  }, [forceUpdate])

  const play = useCallback(async (sampleText: string) => {
    if (!voiceId) return

    if (snapshot.voiceId === voiceId && snapshot.status === "playing") {
      activeAudio?.pause()
      return
    }

    const requestId = ++activeRequest
    releaseActiveAudio()
    setSnapshot({ voiceId, status: "loading", error: null })

    try {
      let url = cachedUrls.get(voiceId)
      if (!url) {
        const blob = await apiFetchBlob("/api/v1/tts/preview", {
          method: "POST",
          body: JSON.stringify({ text: sampleText, voiceType: voiceId, rate: 1, style: "tu_nhien" }),
        })
        if (requestId !== activeRequest) return
        url = URL.createObjectURL(blob)
        cachedUrls.set(voiceId, url)
      }

      if (requestId !== activeRequest) return
      const audio = createAudio(url, voiceId)
      activeAudio = audio
      const playResult = audio.play()
      if (playResult && typeof playResult.catch === "function") {
        playResult.catch(() => {
          if (requestId === activeRequest) setSnapshot({ voiceId, status: "error", error: "playback" })
        })
      }
      if (requestId === activeRequest) setSnapshot({ voiceId, status: "playing", error: null })
    } catch (error) {
      if (requestId === activeRequest) {
        setSnapshot({
          voiceId,
          status: "error",
          error: error instanceof Error ? error.message : "preview",
        })
      }
    }
  }, [voiceId])

  const retry = useCallback((sampleText: string) => {
    if (voiceId) {
      const url = cachedUrls.get(voiceId)
      if (url && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(url)
      cachedUrls.delete(voiceId)
    }
    return play(sampleText)
  }, [play, voiceId])

  const pause = useCallback(() => {
    if (snapshot.voiceId === voiceId) activeAudio?.pause()
  }, [voiceId])

  return {
    activeVoiceId: snapshot.voiceId,
    error: snapshot.voiceId === voiceId ? snapshot.error : null,
    isLoading: snapshot.voiceId === voiceId && snapshot.status === "loading",
    isPlaying: snapshot.voiceId === voiceId && snapshot.status === "playing",
    play,
    pause,
    retry,
  }
}
