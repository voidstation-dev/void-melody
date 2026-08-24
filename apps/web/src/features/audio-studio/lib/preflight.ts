import type { PreflightCheck, PreflightReport, ScriptAnalysisResult } from "../types"

export function evaluatePreflight(
  analysis: ScriptAnalysisResult,
  selectedVoiceId?: string,
  selectedVoiceProvider = "vieneu",
): PreflightReport {
  const checks: PreflightCheck[] = []

  // 1. Content check
  if (!analysis.rawText.trim()) {
    checks.push({
      id: "empty-content",
      severity: "error",
      message: "Chưa có nội dung kịch bản",
      detail: "Nhập hoặc dán văn bản để bắt đầu tạo audio.",
    })
  } else if (analysis.characterCount > 500_000) {
    checks.push({
      id: "char-limit",
      severity: "error",
      message: "Vượt quá giới hạn ký tự (tối đa 500,000 ký tự)",
    })
  } else {
    checks.push({
      id: "content-ready",
      severity: "success",
      message: `${analysis.segments.length} đoạn văn bản (${analysis.characterCount.toLocaleString()} ký tự)`,
    })
  }

  // 2. Voice check
  if (!selectedVoiceId) {
    checks.push({
      id: "no-voice",
      severity: "error",
      message: "Chưa chọn giọng đọc",
      detail: "Vui lòng chọn một giọng đọc từ danh sách.",
    })
  } else {
    checks.push({
      id: "voice-selected",
      severity: "success",
      message: `Giọng đọc: ${selectedVoiceId} (${selectedVoiceProvider})`,
    })
  }

  // 3. Native cues & Provider compatibility
  if (analysis.nativeCueCount > 0) {
    if (selectedVoiceProvider === "vieneu") {
      checks.push({
        id: "native-cues-ok",
        severity: "success",
        message: `${analysis.nativeCueCount}/${analysis.nativeCueCount} native cues được hỗ trợ trực tiếp`,
      })
    } else {
      checks.push({
        id: "native-cues-provider-warn",
        severity: "warning",
        message: `Native cues yêu cầu engine VieNeu (hiện tại: ${selectedVoiceProvider})`,
        detail: "Các thẻ native cue có thể được xử lý như ngữ cảnh hoặc bỏ qua.",
      })
    }
  }

  // 4. Emotion intents check
  if (analysis.emotionCount > 0) {
    checks.push({
      id: "emotion-cues-info",
      severity: "info",
      message: `${analysis.emotionCount} thẻ cảm xúc được áp dụng`,
    })
  }

  // 5. Unsupported cues check
  if (analysis.unsupportedCues.length > 0) {
    checks.push({
      id: "unsupported-cues",
      severity: "warning",
      message: `${analysis.unsupportedCues.length} thẻ không rõ: ${analysis.unsupportedCues.slice(0, 3).join(", ")}`,
      detail: "Các thẻ này sẽ được giữ nguyên dạng văn bản thường khi đọc.",
    })
  }

  const hasErrors = checks.some((c) => c.severity === "error")
  const canGenerate = !hasErrors && analysis.rawText.trim().length > 0 && Boolean(selectedVoiceId)

  return {
    isValid: !hasErrors,
    canGenerate,
    checks,
    stats: {
      segmentCount: analysis.segments.length,
      characterCount: analysis.characterCount,
      nativeCueCount: analysis.nativeCueCount,
      emotionCount: analysis.emotionCount,
      estimatedJobs: analysis.estimatedJobs,
    },
  }
}
