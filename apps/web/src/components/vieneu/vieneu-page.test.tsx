// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VieneuPage } from "./vieneu-page";
import { I18nProvider } from "@/contexts/i18n-provider";

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

vi.mock("@/hooks/use-voice-lab", () => ({
  useVoiceLab: () => ({
    analysis: { data: null, isPending: false, isError: false, mutate: vi.fn(), reset: vi.fn() },
    clone: { data: null, isPending: false, isError: false, mutate: vi.fn(), reset: vi.fn() },
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
    <I18nProvider initialLocale="en">
      <VieneuPage />
    </I18nProvider>
  );
}

describe("VieneuPage", () => {
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
    expect(screen.getByText("sample.wav")).toBeInTheDocument();
    expect(screen.getByText(/analysis pending/i)).toBeInTheDocument();
  });
});
