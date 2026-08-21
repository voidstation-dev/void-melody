/**
 * Audio constraints, supported MIME types, file extensions, and default waveform presets.
 */

export const ACCEPTED_AUDIO_MIME_TYPES = [
  "audio/wav",
  "audio/x-wav",
  "audio/mpeg",
  "audio/mp3",
  "audio/mp4",
  "audio/x-m4a",
] as const;

export const ACCEPTED_AUDIO_EXTENSIONS = [".wav", ".mp3", ".m4a"] as const;

export const MAX_VOICE_SAMPLE_BYTES = 50 * 1024 * 1024; // 50MB

export const DEFAULT_WAVEFORM_PEAKS = [
  24, 42, 30, 64, 48, 78, 54, 36, 70, 46, 82, 58, 32, 66, 44, 74, 40, 60, 28, 52,
  38, 72, 48, 34, 68, 44, 76, 56, 32, 62, 42, 70,
] as const;

export const DEFAULT_WAVE_HEIGHTS = [
  6, 10, 15, 9, 18, 12, 7, 14, 20, 11, 16, 8, 13, 19, 10, 15, 7, 12,
] as const;

export const AUDIO_SPEED_OPTIONS = [
  0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0,
] as const;

export const AUDIO_EXPORT_FORMATS = ["mp3", "m4a", "wav"] as const;
export type AudioExportFormat = (typeof AUDIO_EXPORT_FORMATS)[number];
