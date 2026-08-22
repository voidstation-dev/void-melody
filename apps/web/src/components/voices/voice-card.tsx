import { Voice } from "@/types/voice"
import { PresetVoiceRow } from "./preset-voice-row"

interface VoiceCardProps {
  voice: Voice
  activePlayingVoice?: string | null
  onPlayStart?: (voiceType: string) => void
}

/** @deprecated Use PresetVoiceRow. Kept as a compatibility wrapper for existing consumers. */
export function VoiceCard({ voice, onPlayStart }: VoiceCardProps) {
  return <PresetVoiceRow voice={voice} onPlayStart={onPlayStart} />
}
