// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { I18nProvider } from "@/contexts/i18n-provider"
import { CustomVoiceCard } from "./custom-voice-card"

vi.mock("./voice-preview-button", () => ({
  VoicePreviewButton: () => <button type="button">Nghe thử</button>,
}))

const voice = {
  id: "custom-1",
  display_name: "Adam",
  transcript: "Xin chào",
  consent_given: true,
  created_at: "2026-08-21T00:00:00Z",
  provider_id: "vieneu",
  engine_id: "v3turbo",
  status: "ready",
  quality_score: 92,
  reference_duration_seconds: 6,
  consent_version: "voice-lab-v1",
}

describe("CustomVoiceCard", () => {
  it("confirms deletion through an accessible alert dialog", () => {
    const onDelete = vi.fn()
    render(
      <I18nProvider initialLocale="vi">
        <CustomVoiceCard voice={voice} onDelete={onDelete} />
      </I18nProvider>,
    )

    expect(screen.getByText("VieNeu")).toBeInTheDocument()
    expect(screen.getByText("Chất lượng 92/100")).toBeInTheDocument()
    expect(screen.getByText("Clone")).toBeInTheDocument()
    expect(screen.getByTestId("voice-waveform")).toBeInTheDocument()
    expect(screen.getByRole("article")).toHaveClass("p-3")
    expect(screen.getByRole("heading", { name: "Adam" })).toHaveClass("text-sm")

    fireEvent.click(screen.getByRole("button", { name: /thao tác khác cho custom-1/i }))
    fireEvent.click(screen.getByRole("menuitem", { name: /xóa/i }))

    expect(screen.getByRole("alertdialog")).toHaveTextContent('Xóa giọng "Adam"?')
    fireEvent.click(screen.getByRole("button", { name: "Xóa giọng" }))
    expect(onDelete).toHaveBeenCalledWith("custom-1")
  })
})
