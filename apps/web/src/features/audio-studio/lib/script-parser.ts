import type { CueItem, ScriptAnalysisResult, ScriptSegment } from "../types"
import { findTagByToken } from "./delivery-tags"

const CUE_REGEX = /\[([^\]]+)\]/g

export function parseScript(rawText: string, selectedVoiceProvider = "vieneu"): ScriptAnalysisResult {
  const trimmed = rawText.trim()
  if (!trimmed) {
    return {
      rawText: "",
      segments: [],
      characterCount: 0,
      wordCount: 0,
      nativeCueCount: 0,
      emotionCount: 0,
      deliveryCount: 0,
      totalCueCount: 0,
      unsupportedCues: [],
      estimatedJobs: 0,
    }
  }

  // Split into raw segment lines by newlines (ignoring empty blank rows)
  const rawLines = rawText
    .split(/\r?\n+/)
    .map((l) => l.trim())
    .filter(Boolean)

  let nativeCueCount = 0
  let emotionCount = 0
  let deliveryCount = 0
  const unsupportedCuesSet = new Set<string>()

  const segments: ScriptSegment[] = rawLines.map((line, idx) => {
    const cues: CueItem[] = []
    const matches = [...line.matchAll(CUE_REGEX)]

    for (const match of matches) {
      const rawToken = match[0]
      const tag = findTagByToken(rawToken)

      if (tag) {
        cues.push({
          type: tag.type,
          value: tag.id,
          rawToken,
        })

        if (tag.type === "native") {
          nativeCueCount++
          if (tag.engine && !tag.engine.includes(selectedVoiceProvider)) {
            unsupportedCuesSet.add(`${tag.label} (yêu cầu engine ${tag.engine.join(", ")})`)
          }
        } else if (tag.type === "emotion") {
          emotionCount++
        } else if (tag.type === "delivery") {
          deliveryCount++
        }
      } else {
        unsupportedCuesSet.add(rawToken)
      }
    }

    // Clean text without cue tags for character and sentence reading
    const cleanText = line.replace(CUE_REGEX, "").replace(/\s+/g, " ").trim()

    return {
      id: `segment-${idx + 1}`,
      text: line,
      cleanText,
      cues,
    }
  })

  const characterCount = rawText.length
  const words = rawText.trim().split(/\s+/).filter(Boolean)
  const wordCount = words.length
  const totalCueCount = nativeCueCount + emotionCount + deliveryCount

  // Estimate jobs: 1 job per ~1500 chars or at least 1 job if text exists
  const estimatedJobs = Math.max(1, Math.ceil(characterCount / 1500))

  return {
    rawText,
    segments,
    characterCount,
    wordCount,
    nativeCueCount,
    emotionCount,
    deliveryCount,
    totalCueCount,
    unsupportedCues: Array.from(unsupportedCuesSet),
    estimatedJobs,
  }
}

export function insertTagAtCursor(
  text: string,
  token: string,
  cursorStart: number,
  cursorEnd: number,
): { nextText: string; nextCursorPos: number } {
  const before = text.slice(0, cursorStart)
  const after = text.slice(cursorEnd)

  // Ensure nice spacing around token if needed
  const needsSpaceBefore = before.length > 0 && !before.endsWith(" ") && !before.endsWith("\n")
  const needsSpaceAfter = after.length > 0 && !after.startsWith(" ") && !after.startsWith("\n")

  const insertion = `${needsSpaceBefore ? " " : ""}${token}${needsSpaceAfter ? " " : ""}`
  const nextText = `${before}${insertion}${after}`
  const nextCursorPos = cursorStart + insertion.length

  return { nextText, nextCursorPos }
}
