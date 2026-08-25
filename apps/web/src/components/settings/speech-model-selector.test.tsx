// @vitest-environment jsdom

import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { SpeechModelSelector } from "./speech-model-selector"
import { I18nProvider } from "@/contexts/i18n-provider"
import { QueryProvider } from "@/components/providers/query-provider"
import { useSpeechModelsStore } from "@/stores/speech-models-store"

vi.mock("@/hooks/use-voice-capabilities", () => ({
  useVoiceCapabilities: () => ({
    data: {
      provider_id: "vieneu",
      engine_id: "v3turbo",
      device: "cpu",
      runtime_available: true,
    },
    isLoading: false,
    isError: false,
  }),
}))

function renderSelector() {
  return render(
    <QueryProvider>
      <I18nProvider initialLocale="vi">
        <SpeechModelSelector />
      </I18nProvider>
    </QueryProvider>
  )
}

describe("SpeechModelSelector", () => {
  beforeEach(() => {
    useSpeechModelsStore.setState({
      activeModelId: "small",
      installedModelIds: ["small"],
      downloadingModelId: null,
      downloadProgress: 0,
      autoTranscribeInVoiceLab: true,
      isTranscribing: false,
    })
  })

  it("renders all Whisper models from the catalog", () => {
    renderSelector()

    expect(screen.getByText("Mô hình nhận diện Whisper (ASR)")).toBeInTheDocument()
    expect(screen.getByText("Whisper Tiny")).toBeInTheDocument()
    expect(screen.getByText("Whisper Base")).toBeInTheDocument()
    expect(screen.getByText("Whisper Small")).toBeInTheDocument()
    expect(screen.getByText("Whisper Medium")).toBeInTheDocument()
    expect(screen.getByText("Whisper Large-v3 Turbo")).toBeInTheDocument()
  })

  it("displays CPU hardware recommendation badge for Whisper Small on CPU device", () => {
    renderSelector()

    expect(screen.getByText("CPU Mode")).toBeInTheDocument()
    expect(screen.getByText("★ Khuyên dùng cho CPU")).toBeInTheDocument()
  })

  it("allows switching active model and toggling auto-transcribe", () => {
    useSpeechModelsStore.setState({
      installedModelIds: ["tiny", "small"],
      activeModelId: "small",
    })

    renderSelector()

    const activateBtns = screen.getAllByRole("button", { name: "Kích hoạt" })
    expect(activateBtns.length).toBeGreaterThanOrEqual(1)

    fireEvent.click(activateBtns[0])
    expect(useSpeechModelsStore.getState().activeModelId).toBe("tiny")

    const toggle = screen.getByRole("checkbox") as HTMLInputElement
    expect(toggle.checked).toBe(true)

    fireEvent.click(toggle)
    expect(useSpeechModelsStore.getState().autoTranscribeInVoiceLab).toBe(false)
  })
})
