// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { EmotionalScriptPage } from "./emotional-script-page"
import { apiFetch, apiFetchBlob } from "@/lib/api-client"

vi.mock("@/hooks/use-voices", () => ({
  useVoices: () => ({
    data: {
      items: [{
        id: "Minh Đức",
        voiceType: "Minh Đức",
        displayName: "Minh Đức",
        languageCode: "vi-VN",
        languageShort: "vi",
        resourceId: null,
        capturedAt: null,
        providerId: "vieneu",
      }],
    },
  }),
}))

vi.mock("@/hooks/use-custom-voices", () => ({
  useCustomVoices: () => ({ data: { items: [] } }),
}))

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
  apiFetchBlob: vi.fn(),
  resolveApiUrl: (path: string) => `http://localhost:8000${path}`,
}))

const parsedDocument = {
  version: 1,
  id: "",
  title: "Kịch bản chưa đặt tên",
  revision: 1,
  source: { type: "quick_text", original_name: null },
  defaults: { voice_id: null, global_delivery_prompt: null, base_rate: 1, pause_profile: "normal" },
  speakers: [],
  scenes: [{
    id: "scene-1",
    title: "Cảnh 1",
    order: 0,
    lines: [{
      id: "line-1-1",
      order: 0,
      speaker_id: null,
      text: "Một câu chuyện ngắn.",
      delivery: { intent: "neutral", intensity: 0.5, nonverbals: [], pause_before_ms: 0, pause_after_ms: 0 },
      source_timing: null,
    }],
  }],
  warnings: [],
}

const completedRender = {
  id: "render-1",
  script_id: "script-1",
  script_revision: 1,
  status: "completed",
  stage: "completed",
  progress: 100,
  total_segments: 1,
  cached_segments: 1,
  completed_segments: 1,
  failed_segments: 0,
  output_format: "mp3",
  output_duration: 2,
  output_file_size: 100,
  output_url: "/api/v1/script-renders/render-1/audio",
  error_code: null,
  error_message: null,
  segments: [],
}

describe("EmotionalScriptPage audio playback", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ document: parsedDocument, line_count: 1, speaker_count: 0, warning_count: 0 } as never)
      .mockResolvedValueOnce({ id: "script-1" } as never)
      .mockResolvedValueOnce(completedRender as never)
    vi.mocked(apiFetchBlob).mockResolvedValue(new Blob(["audio"], { type: "audio/mpeg" }))
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn().mockReturnValue("blob:script-audio"),
      revokeObjectURL: vi.fn(),
    })
  })

  it("loads completed render audio through the authenticated blob client", async () => {
    render(<EmotionalScriptPage />)
    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung hoặc kịch bản/), {
      target: { value: "Một câu chuyện ngắn." },
    })
    fireEvent.click(screen.getByRole("button", { name: "Tạo audio" }))

    await screen.findByText("Bản thu đã sẵn sàng.")
    await waitFor(() => {
      expect(apiFetchBlob).toHaveBeenCalledWith("/api/v1/script-renders/render-1/audio")
    })
  })
})
