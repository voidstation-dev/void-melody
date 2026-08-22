import { describe, expect, it } from "vitest"
import { matchesVoiceFilters } from "./voice-library-utils"

describe("matchesVoiceFilters", () => {
  it("matches display name, provider and language without case sensitivity", () => {
    const voice = {
      displayName: "Nhỏ Ngọt Ngào",
      voiceType: "BV421_vivn_streaming",
      languageCode: "vi-VN",
      providerId: "capcut",
    }

    expect(matchesVoiceFilters(voice, "ngọt", "all", "all")).toBe(true)
    expect(matchesVoiceFilters(voice, "capcut", "capcut", "all")).toBe(true)
    expect(matchesVoiceFilters(voice, "", "vieneu", "all")).toBe(false)
    expect(matchesVoiceFilters(voice, "", "all", "en-US")).toBe(false)
  })
})
