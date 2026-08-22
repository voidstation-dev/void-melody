// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { I18nProvider } from "@/contexts/i18n-provider"
import { PresetVoiceRow } from "./preset-voice-row"

vi.mock("./voice-preview-button", () => ({
  VoicePreviewButton: ({ voiceId }: { voiceId: string }) => <button type="button">Preview {voiceId}</button>,
}))

const voice = {
  id: "voice-1",
  languageCode: "vi-VN",
  languageShort: "vi",
  voiceType: "BV421_vivn_streaming",
  displayName: "Nhỏ Ngọt Ngào",
  resourceId: "resource-1",
  capturedAt: null,
  providerId: "capcut",
  gender: "female",
  region: "Bắc",
  style: "tu_nhien",
  description: "Nữ · Bắc · Phong cách tự nhiên",
}

describe("PresetVoiceRow", () => {
  it("keeps the use route and presents compact catalog metadata", () => {
    render(
      <I18nProvider initialLocale="vi">
        <PresetVoiceRow voice={voice} />
      </I18nProvider>,
    )

    expect(screen.getByText("Nhỏ Ngọt Ngào")).toBeInTheDocument()
    expect(screen.getByText(/vi-VN/)).toBeInTheDocument()
    expect(screen.getByText(/Mẫu có sẵn/)).toBeInTheDocument()
    expect(screen.getByText("CapCut")).toBeInTheDocument()
    expect(screen.getByText("Tự nhiên")).toBeInTheDocument()
    expect(screen.getByText("Nữ · Bắc · Tự nhiên")).toBeInTheDocument()
    expect(screen.getByTestId("voice-waveform")).toBeInTheDocument()
    expect(screen.getByRole("article")).toHaveClass("min-h-[300px]")
    expect(screen.getByRole("article")).toHaveClass("p-4")
    expect(screen.getByRole("heading", { name: "Nhỏ Ngọt Ngào" })).toHaveClass("text-2xl")
    expect(screen.getByRole("link", { name: /dùng giọng/i })).toHaveAttribute(
      "href",
      "/?voice=BV421_vivn_streaming",
    )
    expect(screen.getByRole("button", { name: /preview bv421_vivn_streaming/i })).toBeInTheDocument()
  })
})
