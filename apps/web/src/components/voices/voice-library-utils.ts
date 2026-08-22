import { CustomVoice, Voice } from "@/types/voice"

export type VoiceLibraryTab = "all" | "preset" | "custom"
export type VoiceFilterValue = "all" | string

type FilterableVoice = Pick<Voice, "displayName" | "voiceType" | "languageCode"> & {
  providerId?: string | null
}

export function providerLabel(providerId?: string | null) {
  switch (providerId?.toLowerCase()) {
    case "vieneu":
      return "VieNeu"
    case "omnivoice":
      return "OmniVoice"
    case "capcut":
      return "CapCut"
    default:
      return providerId || "—"
  }
}

export function customVoiceAsFilterable(voice: CustomVoice): FilterableVoice {
  return {
    displayName: voice.display_name,
    voiceType: voice.id,
    languageCode: "vi-VN",
    providerId: voice.provider_id,
  }
}

export function matchesVoiceFilters(
  voice: FilterableVoice,
  search: string,
  provider: VoiceFilterValue = "all",
  language: VoiceFilterValue = "all",
) {
  const query = search.trim().toLocaleLowerCase()
  const providerId = voice.providerId?.toLocaleLowerCase() || ""
  const languageCode = voice.languageCode?.toLocaleLowerCase() || ""
  const searchable = [voice.displayName, voice.voiceType, voice.languageCode, providerId, providerLabel(voice.providerId)]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase()

  return (
    (!query || searchable.includes(query)) &&
    (provider === "all" || providerId === provider.toLocaleLowerCase()) &&
    (language === "all" || languageCode === language.toLocaleLowerCase())
  )
}

export function getVoiceProviders(voices: Array<Pick<Voice, "providerId">>) {
  return Array.from(new Set(voices.map((voice) => voice.providerId).filter(Boolean) as string[])).sort()
}

export function getVoiceLanguages(voices: Array<Pick<Voice, "languageCode">>) {
  return Array.from(new Set(voices.map((voice) => voice.languageCode).filter(Boolean))).sort()
}
