import { MAX_BATCH_FILES, MAX_BATCH_TOTAL_CHARS } from "@/constants";

export { MAX_BATCH_FILES, MAX_BATCH_TOTAL_CHARS };

export type BatchLimitError =
  | "BATCH_FILE_LIMIT_EXCEEDED"
  | "BATCH_TEXT_LIMIT_EXCEEDED"

export function getBatchLimitError(
  files: ReadonlyArray<{ text: string }>,
): BatchLimitError | null {
  if (files.length > MAX_BATCH_FILES) {
    return "BATCH_FILE_LIMIT_EXCEEDED"
  }

  const totalCharacters = files.reduce(
    (total, file) => total + file.text.length,
    0,
  )
  if (totalCharacters > MAX_BATCH_TOTAL_CHARS) {
    return "BATCH_TEXT_LIMIT_EXCEEDED"
  }
  return null
}
