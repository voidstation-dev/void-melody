import { describe, expect, it } from "vitest"
import { parseScript, insertTagAtCursor } from "./script-parser"
import { evaluatePreflight } from "./preflight"

describe("Audio Studio Script Parser", () => {
  it("parses empty string cleanly", () => {
    const res = parseScript("")
    expect(res.characterCount).toBe(0)
    expect(res.segments).toHaveLength(0)
    expect(res.nativeCueCount).toBe(0)
    expect(res.emotionCount).toBe(0)
  })

  it("parses native cues and emotion tags correctly", () => {
    const text = "[cười] Chào bạn nhé!\n[bình tĩnh] Hôm nay trời rất đẹp."
    const res = parseScript(text, "vieneu")

    expect(res.segments).toHaveLength(2)
    expect(res.nativeCueCount).toBe(1) // [cười]
    expect(res.emotionCount).toBe(1) // [bình tĩnh]
    expect(res.unsupportedCues).toHaveLength(0)
    expect(res.segments[0].cleanText).toBe("Chào bạn nhé!")
    expect(res.segments[1].cleanText).toBe("Hôm nay trời rất đẹp.")
  })

  it("detects unsupported cues when engine is not vieneu", () => {
    const text = "[cười] Xin chào!"
    const res = parseScript(text, "capcut")

    expect(res.nativeCueCount).toBe(1)
    expect(res.unsupportedCues.length).toBeGreaterThan(0)
  })

  it("inserts tag token at cursor with proper whitespace", () => {
    const text = "Xin chào các bạn."
    const { nextText } = insertTagAtCursor(text, "[cười]", 8, 8)
    expect(nextText).toBe("Xin chào [cười] các bạn.")
  })
})

describe("Audio Studio Preflight", () => {
  it("evaluates valid script and voice properly", () => {
    const analysis = parseScript("Xin chào [cười]!", "vieneu")
    const report = evaluatePreflight(analysis, "BV421_vivn_streaming", "vieneu")

    expect(report.canGenerate).toBe(true)
    expect(report.isValid).toBe(true)
    expect(report.stats.segmentCount).toBe(1)
    expect(report.stats.nativeCueCount).toBe(1)
  })

  it("blocks generation when text is empty or voice is missing", () => {
    const analysis = parseScript("", "vieneu")
    const report = evaluatePreflight(analysis, "", "vieneu")

    expect(report.canGenerate).toBe(false)
    expect(report.isValid).toBe(false)
  })
})
