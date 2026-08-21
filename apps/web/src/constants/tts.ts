/**
 * Text-to-speech batch limits, acceptable text formats, and playback defaults.
 */

export const MAX_BATCH_FILES = 50;
export const MAX_BATCH_TOTAL_CHARS = 500_000;

export const ACCEPTED_TEXT_EXTENSIONS = [".txt"] as const;
export const ACCEPTED_TEXT_MIME_TYPES = ["text/plain"] as const;

export const DEFAULT_TTS_SPEED = 1.0;
export const DEFAULT_TTS_PITCH = 0;
