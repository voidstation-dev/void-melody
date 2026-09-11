// @vitest-environment jsdom

import { describe, expect, it, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { VoxCpmPage } from "./voxcpm-page"
import { I18nProvider } from "@/contexts/i18n-provider"
import { useVoxCpmStore, type VoxCpmState } from "@/stores/voxcpm-store"

function renderPage() {
  return render(
    <I18nProvider>
      <VoxCpmPage />
    </I18nProvider>,
  )
}

const initialStoreState = {
  activeTab: "clone",
  runtime: null,
  isLoadingRuntime: false,
  runtimeError: null,
  clonedVoices: [],
  isLoadingVoices: false,
  voicesError: null,
  emotionPresetId: "neutral",
  customInstruction: "",
  targetText: "",
  selectedVoiceId: null,
} as Partial<VoxCpmState>

describe("VoxCpmPage", () => {
  beforeEach(() => {
    useVoxCpmStore.setState(initialStoreState)
  })

  it("renders title and mock runtime badge", async () => {
    renderPage()
    expect(screen.getByText("VoxCPM2 Studio")).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText(/Runtime sẵn sàng/)).toBeInTheDocument()
    })
  })

  it("shows all 4 tabs", () => {
    renderPage()
    expect(screen.getByRole("tab", { name: "Clone giọng" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "TTS cảm xúc" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Giọng đã clone" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Runtime" })).toBeInTheDocument()
  })

  // Radix Tabs activates triggers on mousedown, not click.
  function selectTab(name: string | RegExp) {
    const tab = screen.getByRole("tab", { name })
    fireEvent.mouseDown(tab)
    fireEvent.click(tab)
  }

  it("switches between all 4 tabs", () => {
    renderPage()
    selectTab("TTS cảm xúc")
    expect(useVoxCpmStore.getState().activeTab).toBe("emotional")
    selectTab("Giọng đã clone")
    expect(useVoxCpmStore.getState().activeTab).toBe("voices")
    selectTab("Runtime")
    expect(useVoxCpmStore.getState().activeTab).toBe("runtime")
    selectTab("Clone giọng")
    expect(useVoxCpmStore.getState().activeTab).toBe("clone")
  })

  it("clone tab shows the clone flow sections", () => {
    renderPage()
    expect(screen.getByText("1. Chọn audio tham chiếu")).toBeInTheDocument()
    expect(screen.getByText("3. Tạo giọng clone")).toBeInTheDocument()
    expect(screen.getByTestId("voxcpm-create-voice")).toBeInTheDocument()
  })

  it("create button disabled until file + name + consent", () => {
    renderPage()
    expect(screen.getByTestId("voxcpm-create-voice")).toBeDisabled()
    fireEvent.change(screen.getByTestId("voxcpm-voice-name"), {
      target: { value: "Giọng test" },
    })
    fireEvent.click(screen.getByTestId("voxcpm-consent"))
    // Still disabled without analysis + file
    expect(screen.getByTestId("voxcpm-create-voice")).toBeDisabled()
  })

  it("voices tab lists mock cloned voices", async () => {
    renderPage()
    selectTab("Giọng đã clone")
    await waitFor(() => {
      expect(screen.getByText("Giọng demo Nam")).toBeInTheDocument()
    })
    expect(screen.getByText("Giọng demo Nữ")).toBeInTheDocument()
  })

  it("runtime tab shows mock runtime rows", async () => {
    renderPage()
    selectTab("Runtime")
    await waitFor(() => {
      expect(screen.getByText("mock")).toBeInTheDocument()
    })
    expect(screen.getByText("48 kHz")).toBeInTheDocument()
    expect(screen.getByText("voxcpm2")).toBeInTheDocument()
  })

  it("emotional tab has voice select, emotion preset and disabled generate", () => {
    renderPage()
    selectTab("TTS cảm xúc")
    expect(screen.getByText("Giọng đã chọn")).toBeInTheDocument()
    expect(screen.getByText("Cảm xúc")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Tạo âm thanh/ })).toBeDisabled()
  })

  it("runtime badge shows checking state before runtime loads", () => {
    useVoxCpmStore.setState({ runtime: null, isLoadingRuntime: true })
    renderPage()
    expect(screen.getByText("Đang kiểm tra runtime…")).toBeInTheDocument()
  })

  it("emotional tab enables generate with voice + text (Phase 5)", () => {
    useVoxCpmStore.setState({
      clonedVoices: [
        {
          id: "v1",
          display_name: "Voice One",
          reference_duration_seconds: 4,
          sample_rate: 48000,
          created_at: "2026-01-01",
        },
      ],
      selectedVoiceId: "v1",
      targetText: "Xin chào",
      emotionPresetId: "sad",
      generation: null,
    })
    renderPage()
    selectTab("TTS cảm xúc")
    expect(screen.getByRole("button", { name: /Tạo âm thanh/ })).not.toBeDisabled()
  })

  it("emotional tab shows audio result when generation exists (Phase 5)", () => {
    useVoxCpmStore.setState({
      clonedVoices: [
        {
          id: "v1",
          display_name: "Voice One",
          reference_duration_seconds: 4,
          sample_rate: 48000,
          created_at: "2026-01-01",
        },
      ],
      selectedVoiceId: "v1",
      targetText: "Xin chào",
      generation: {
        audio_url: "/api/v1/voxcpm/generations/abc123",
        output_path: "C:/tmp/abc123.wav",
        sample_rate: 48000,
        duration_seconds: 2.4,
        method: "synthesize_emotional",
        instruction: "Sad",
        voice_id: "v1",
        emotion: "sad",
      },
    })
    renderPage()
    selectTab("TTS cảm xúc")
    expect(screen.getByTestId("voxcpm-generation-result")).toBeInTheDocument()
    const player = screen
      .getByTestId("voxcpm-generation-result")
      .querySelector("audio")
    expect(player).not.toBeNull()
    expect(player?.getAttribute("src")).toContain("/api/v1/voxcpm/generations/abc123")
  })

  it("generate button disabled without text or voice (Phase 5)", () => {
    renderPage()
    selectTab("TTS cảm xúc")
    expect(screen.getByRole("button", { name: /Tạo âm thanh/ })).toBeDisabled()
  })
})
