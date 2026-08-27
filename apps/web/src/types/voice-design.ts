export type VoiceDesignCapabilities = {
  enabled: boolean
  providerId: string
  engineId: string
  modelInstalled: boolean
  supportsPromptDesign: boolean
  supportsVoiceClone: boolean
  reasonCode?: string | null
  reason?: string | null
}

export type VoiceDesignPreviewRequest = {
  prompt?: string
  language?: string
  previewText?: string
  count?: number
  attributes?: Record<string, string | null>
}

export type VoiceDesignCandidate = {
  id: string
  audioUrl: string
}

export type VoiceDesignPreviewResponse = {
  sessionId: string
  compiledInstruction: string
  candidates: VoiceDesignCandidate[]
}

export type VoiceDesignCommitRequest = {
  candidateId: string
  displayName: string
}

export type VoiceDesignCommitResponse = {
  voiceId: string
  displayName: string
  providerId: string
  engineId: string
  voiceKind: string
  status: string
}

export type VoiceDesignSession = {
  sessionId: string
  compiledInstruction: string
  previewText: string
  language: string | null
  status: string
  candidates: VoiceDesignCandidate[]
}
