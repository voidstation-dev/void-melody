// @vitest-environment jsdom

import { describe, expect, it, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react"
import { CloneVoiceTab } from "./clone-voice-tab"
import { I18nProvider } from "@/contexts/i18n-provider"
import { useVoxCpmStore, type VoxCpmState } from "@/stores/voxcpm-store"
import type { VoxCpmAnalysisResult } from "@/types/voxcpm"

const ANALYSIS: VoxCpmAnalysisResult = {
  duration_seconds: 6.0,
  source_duration_seconds: 6.0,
  selected_start_seconds: 1.0,
  selected_end_seconds: 5.5,
  reference_duration_seconds: 4.5,
  speech_ratio: 0.82,
  noise_level_db: -38.5,
  clipping_ratio: 0.001,
  quality_score: 84,
  waveform_peaks: Array.from({ length: 48 }, (_, i) => 0.2 + 0.6 * Math.abs(Math.sin(i / 5))),
  warnings: ["High background noise detected; denoise cleanup is recommended."],
  recommended_start_seconds: 1.0,
  recommended_end_seconds: 5.5,
  metrics: { speech_score: 80, noise_score: 70, clipping_score: 95, stability_score: 75, segment_score: 80 },
}

const initialStoreState = {
  activeTab: "clone" as const,
  analysis: null as VoxCpmAnalysisResult | null,
  isAnalyzing: false,
  isCreatingVoice: false,
  cloneError: null as string | null,
  clonedVoices: [],
  isLoadingVoices: false,
  voicesError: null as string | null,
  runtime: null,
  isLoadingRuntime: false,
  runtimeError: null as string | null,
  emotionPresetId: "neutral",
  customInstruction: "",
  targetText: "",
  selectedVoiceId: null,
} as Partial<VoxCpmState>

function renderTab() {
  return render(
    <I18nProvider>
      <CloneVoiceTab />
    </I18nProvider>,
  )
}

describe("CloneVoiceTab", () => {
  beforeEach(() => {
    useVoxCpmStore.setState(initialStoreState)
  })

  afterEach(() => {
    cleanup()
    useVoxCpmStore.setState(initialStoreState)
  })

  it("renders the clone sections (trim section only with a selected file)", () => {
    renderTab()
    expect(screen.getByText("1. Chọn audio tham chiếu")).toBeInTheDocument()
    expect(screen.getByText("3. Tạo giọng clone")).toBeInTheDocument()
  })

  it("hides trim section and create is disabled without analysis", () => {
    renderTab()
    expect(screen.queryByTestId("voxcpm-trim-section")).not.toBeInTheDocument()
    expect(screen.getByTestId("voxcpm-create-voice")).toBeDisabled()
  })

  it("shows analysis panel with quality, noise, speech ratio and waveform when analysis exists", () => {
    useVoxCpmStore.setState({ analysis: ANALYSIS })
    renderTab()
    expect(screen.getByTestId("voxcpm-analysis-panel")).toBeInTheDocument()
    expect(screen.getByTestId("voxcpm-quality")).toHaveTextContent("84")
    expect(screen.getByTestId("voxcpm-trim-section")).toBeInTheDocument()
    // waveform bars rendered
    expect(screen.getAllByTestId("voxcpm-waveform-bar").length).toBe(48)
    // warning list shown
    expect(screen.getByText(/High background noise/)).toBeInTheDocument()
  })

  it("shows trim inputs seeded from analysis selection", () => {
    useVoxCpmStore.setState({ analysis: ANALYSIS })
    renderTab()
    const startInput = screen.getByLabelText("Bắt đầu (giây)") as HTMLInputElement
    const endInput = screen.getByLabelText("Kết thúc (giây)") as HTMLInputElement
    expect(startInput.value).toBe("1")
    expect(endInput.value).toBe("5.5")
  })

  it("shows error message from store", () => {
    useVoxCpmStore.setState({ cloneError: "Không thể phân tích tệp audio. Vui lòng thử lại." })
    renderTab()
    expect(screen.getByTestId("voxcpm-clone-error")).toHaveTextContent("Không thể phân tích")
  })

  it("shows analyzing state on choose-file button", () => {
    useVoxCpmStore.setState({ isAnalyzing: true })
    renderTab()
    expect(screen.getByTestId("voxcpm-choose-file")).toHaveTextContent("Đang phân tích…")
    expect(screen.getByTestId("voxcpm-choose-file")).toBeDisabled()
  })

  it("shows creating state on submit button", () => {
    useVoxCpmStore.setState({ analysis: ANALYSIS, isCreatingVoice: true })
    renderTab()
    const button = screen.getByTestId("voxcpm-create-voice")
    expect(button).toHaveTextContent("Đang tạo giọng…")
  })

  it("create button enables with file + name + consent (analysis mocked in store)", async () => {
    // Stub the store's analyze call so file selection does not hit the network.
    useVoxCpmStore.setState({
      analysis: ANALYSIS,
      analyzeReference: async () => {
        useVoxCpmStore.setState({ analysis: ANALYSIS })
        return true
      },
    })
    renderTab()
    const button = screen.getByTestId("voxcpm-create-voice")
    expect(button).toBeDisabled()
    const testFile = new File(["audio-bytes"], "ref.wav", { type: "audio/wav" })
    await waitFor(() => {
      fireEvent.change(screen.getByTestId("voxcpm-file-input"), {
        target: { files: [testFile] },
      })
    })
    fireEvent.change(screen.getByTestId("voxcpm-voice-name"), { target: { value: "Giọng MC" } })
    fireEvent.click(screen.getByTestId("voxcpm-consent"))
    await waitFor(() => {
      expect(button).toBeEnabled()
    })
  })
})