// @vitest-environment jsdom

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { VoiceCard } from "./voice-card"
import * as apiClient from "@/lib/api-client"
import { I18nProvider } from "@/contexts/i18n-provider"

const mockVoice = {
  id: "voice-1",
  languageCode: "vi-VN",
  languageShort: "vi",
  voiceType: "BV421_vivn_streaming",
  displayName: "Nhỏ Ngọt Ngào",
  resourceId: "resource-1",
  capturedAt: null,
}

function renderVoiceCard(props: React.ComponentProps<typeof VoiceCard>, locale: "vi" | "en" = "vi") {
  return render(
    <I18nProvider initialLocale={locale}>
      <VoiceCard {...props} />
    </I18nProvider>
  )
}

describe("VoiceCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined)
    window.HTMLMediaElement.prototype.pause = vi.fn()
    if (!global.URL.createObjectURL) {
      global.URL.createObjectURL = vi.fn()
    }
    if (!global.URL.revokeObjectURL) {
      global.URL.revokeObjectURL = vi.fn()
    }
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("renders voice details and preview button", () => {
    renderVoiceCard({ voice: mockVoice }, "vi")

    expect(screen.getByText("Nhỏ Ngọt Ngào")).toBeInTheDocument()
    expect(screen.getByText(/Giọng đọc mẫu chuẩn studio/i)).toBeInTheDocument()
    expect(screen.getByText("vi-VN")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /nghe thử nhỏ ngọt ngào/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dùng giọng/i })).toHaveAttribute("href", "/?voice=BV421_vivn_streaming")
  })

  it("fetches preview audio and starts playback on click", async () => {
    const fakeBlob = new Blob(["fake-audio"], { type: "audio/mpeg" })
    const apiFetchBlobSpy = vi.spyOn(apiClient, "apiFetchBlob").mockResolvedValue(fakeBlob)
    const createObjectURLSpy = vi.spyOn(global.URL, "createObjectURL").mockReturnValue("blob:http://localhost/test-audio-url")

    const onPlayStart = vi.fn()
    renderVoiceCard({ voice: mockVoice, onPlayStart }, "vi")

    const previewBtn = screen.getByRole("button", { name: /nghe thử nhỏ ngọt ngào/i })
    fireEvent.click(previewBtn)

    await waitFor(() => {
      expect(apiFetchBlobSpy).toHaveBeenCalledWith(
        "/api/v1/tts/preview",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            text: "Xin chào, đây là bản nghe thử giọng đọc Nhỏ Ngọt Ngào.",
            voiceType: "BV421_vivn_streaming",
            rate: 1.0,
            style: "tu_nhien",
          }),
        }),
      )
    })

    expect(createObjectURLSpy).toHaveBeenCalledWith(fakeBlob)
    expect(onPlayStart).toHaveBeenCalledWith("BV421_vivn_streaming")
  })

  it("displays error message if preview request fails", async () => {
    vi.spyOn(apiClient, "apiFetchBlob").mockRejectedValue(new Error("Mất kết nối API"))

    renderVoiceCard({ voice: mockVoice }, "vi")

    const previewBtn = screen.getByRole("button", { name: /nghe thử nhỏ ngọt ngào/i })
    fireEvent.click(previewBtn)

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Mất kết nối API")
    })
  })
})
