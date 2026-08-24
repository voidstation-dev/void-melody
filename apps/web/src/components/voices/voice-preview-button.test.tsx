// @vitest-environment jsdom

import { describe, expect, it, vi, beforeEach } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { I18nProvider } from "@/contexts/i18n-provider"
import { VoicePreviewButton } from "./voice-preview-button"
import * as apiClient from "@/lib/api-client"

function renderButton(props: Partial<React.ComponentProps<typeof VoicePreviewButton>> = {}) {
  return render(
    <I18nProvider initialLocale="vi">
      <VoicePreviewButton voiceId="voice-1" sampleText="Xin chào" {...props} />
    </I18nProvider>,
  )
}

describe("VoicePreviewButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined)
    window.HTMLMediaElement.prototype.pause = vi.fn()
    global.URL.createObjectURL = vi.fn().mockReturnValue("blob:test")
    global.URL.revokeObjectURL = vi.fn()
  })

  it("requests the shared preview endpoint and announces the playing state", async () => {
    const apiFetchBlobSpy = vi.spyOn(apiClient, "apiFetchBlob").mockResolvedValue(new Blob(["audio"]))

    renderButton()
    fireEvent.click(screen.getByRole("button", { name: /nghe thử voice-1/i }))

    await waitFor(() => {
      expect(apiFetchBlobSpy).toHaveBeenCalledWith(
        "/api/v1/tts/preview",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            text: "Xin chào",
            voiceType: "voice-1",
            rate: 1,
            style: "tu_nhien",
          }),
        }),
      )
    })

    expect(await screen.findByRole("button", { name: /đang phát voice-1/i })).toBeInTheDocument()
  })

  it("shows a recoverable error when preview generation fails", async () => {
    vi.spyOn(apiClient, "apiFetchBlob").mockRejectedValue(new Error("Mất kết nối API"))

    renderButton()
    fireEvent.click(screen.getByRole("button", { name: /nghe thử voice-1/i }))

    expect(await screen.findByRole("alert")).toHaveTextContent("Mất kết nối API")
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument()
  })

  it("supports the compact circular preview treatment", () => {
    renderButton({ compact: true })

    const button = screen.getByRole("button", { name: /nghe thử voice-1/i })
    expect(button).toHaveClass("rounded-full")
    expect(button).toHaveClass("h-16")
    expect(button).toHaveClass("w-16")
    expect(screen.getByText("Nghe thử")).toHaveClass("sr-only")
  })

  it("switches the active playback state when another voice is previewed", async () => {
    vi.spyOn(apiClient, "apiFetchBlob").mockResolvedValue(new Blob(["audio"]))

    render(
      <I18nProvider initialLocale="vi">
        <VoicePreviewButton voiceId="voice-1" sampleText="Một" />
        <VoicePreviewButton voiceId="voice-2" sampleText="Hai" />
      </I18nProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: /nghe thử voice-1/i }))
    expect(await screen.findByRole("button", { name: /đang phát voice-1/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /nghe thử voice-2/i }))
    expect(await screen.findByRole("button", { name: /đang phát voice-2/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /nghe thử voice-1/i })).toBeInTheDocument()
  })
})
