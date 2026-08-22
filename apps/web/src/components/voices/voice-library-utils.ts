import { CustomVoice, Voice } from "@/types/voice"

export type VoiceLibraryTab = "all" | "preset" | "custom"
export type VoiceFilterValue = "all" | string

type FilterableVoice = Pick<Voice, "displayName" | "voiceType" | "languageCode" | "gender" | "region" | "style" | "description"> & {
  providerId?: string | null
}

const styleLabels: Record<string, string> = {
  tu_nhien: "Tự nhiên",
  tin_tuc: "Tin tức",
  doc_truyen: "Đọc truyện",
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
    gender: null,
    region: null,
    style: null,
    description: voice.transcript,
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
  const genderLabel = voice.gender === "male" ? "Nam male" : voice.gender === "female" ? "Nữ female" : ""
  const styleLabel = voice.style ? `${styleLabels[voice.style] || voice.style} ${voice.style}` : ""
  const searchable = [voice.displayName, voice.voiceType, voice.languageCode, providerId, providerLabel(voice.providerId), genderLabel, voice.region, styleLabel, voice.description]
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
