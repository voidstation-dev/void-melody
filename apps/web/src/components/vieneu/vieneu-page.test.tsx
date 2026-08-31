// @vitest-environment jsdom

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VieneuPage } from "./vieneu-page";
import { I18nProvider } from "@/contexts/i18n-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { useVoiceLabStore } from "@/stores/voice-lab-store";

vi.mock("@/lib/voice-lab-api", () => ({
  analyzeVoiceSample: vi.fn().mockImplementation(() => new Promise(() => {})),
  cloneVoiceProfile: vi.fn().mockResolvedValue({ id: "mock-id", display_name: "Mock Voice" }),
  getVoiceCalibrationAudioUrl: vi.fn().mockReturnValue("/mock-calibration.wav"),
}));

vi.mock("@/hooks/use-voice-capabilities", () => ({
  useVoiceCapabilities: () => ({
    data: {
      provider_id: "vieneu",
      engine_id: "v3turbo",
      engine_version: "3.2.4",
      runtime_available: true,
      device: "cpu",
      backend: "onnx",
      supports_preset_voices: true,
      supports_voice_cloning: true,
      supports_denoise: true,
      supports_streaming: true,
      reason_code: null,
      reason: null,
    },
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-tts-job", () => ({
  useTTSJob: () => ({ data: null }),
}));

vi.mock("@/hooks/use-custom-voice", () => ({
  useCustomVoice: () => ({ data: null, isLoading: false, isError: false }),
}));

function renderVieneu() {
  return render(
    <QueryProvider>
      <I18nProvider initialLocale="en">
        <VieneuPage />
      </I18nProvider>
    </QueryProvider>
  );
}

describe("VieneuPage", () => {
  beforeEach(() => {
    useVoiceLabStore.getState().reset();
  });
  it("renders the Voice Lab workspace and runtime status", () => {
    renderVieneu();

    expect(screen.getByRole("heading", { name: "Voice Lab" })).toBeInTheDocument();
    expect(screen.getByText(/clone ready/i)).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /preset voices/i })).not.toBeInTheDocument();
  });

  it("keeps the Voice Lab focused on voice cloning by default", () => {
    renderVieneu();
    expect(screen.getByRole("heading", { name: /upload reference audio/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /preset voices/i })).not.toBeInTheDocument();
  });

  it("keeps Create Voice gated until a reference is ready", () => {
    renderVieneu();
    expect(screen.getByRole("heading", { name: /upload reference audio/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /preview & output/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create voice/i })).toBeDisabled();
  });

  it("renders a selected audio file without calling a backend", () => {
    renderVieneu();
    const input = screen.getByLabelText(/voice sample file/i) as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], "sample.wav", { type: "audio/wav" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getAllByText("sample.wav").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/analysis pending/i)).toBeInTheDocument();
  });

  it("renders denoise mode and clone mode selectors in step 3", () => {
    renderVieneu();
    expect(screen.getByLabelText(/denoise mode/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/voice clone mode/i)).toBeInTheDocument();
  });

  it("restores active cloning progress when navigating back to Voice Lab", () => {
    useVoiceLabStore.setState({
      isCloning: true,
      cloneProgress: 75,
      cloneStage: "Extracting timbre characteristics...",
    });

    renderVieneu();

    expect(screen.getByText("Extracting timbre characteristics...")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("restores completed voice profile and allows resetting", () => {
    useVoiceLabStore.setState({
      createdProfile: {
        id: "cloned-voice-123",
        display_name: "My Cloned Voice",
        provider_id: "vieneu",
        engine_id: "v3turbo",
        status: "ready",
        calibration_available: false,
      } as any,
    });

    renderVieneu();

    expect(screen.getAllByText("My Cloned Voice").length).toBeGreaterThanOrEqual(1);
    const resetBtn = screen.getByRole("button", { name: /create another voice/i });
    expect(resetBtn).toBeInTheDocument();

    fireEvent.click(resetBtn);
    expect(useVoiceLabStore.getState().createdProfile).toBeNull();
  });
});
