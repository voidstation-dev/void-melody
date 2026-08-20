// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VieneuPage } from "./vieneu-page";

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

describe("VieneuPage", () => {
  it("renders the Voice Lab workspace and runtime status", () => {
    render(<VieneuPage />);

    expect(screen.getByRole("heading", { name: "Voice Lab" })).toBeInTheDocument();
    expect(screen.getByText(/clone ready/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /preset voices/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /clone voice/i })).toBeInTheDocument();
  });

  it("shows the preset-voices section by default", () => {
    render(<VieneuPage />);
    expect(screen.getByRole("heading", { name: /preset voices/i })).toBeInTheDocument();
  });

  it("switches to the cloning workspace and keeps Create Voice gated", () => {
    render(<VieneuPage />);
    const cloningToggle = screen.getByRole("tab", { name: /clone voice/i });
    fireEvent.click(cloningToggle);
    expect(screen.getByRole("heading", { name: /upload sample/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /preview & output/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create voice/i })).toBeDisabled();
    expect(cloningToggle).toHaveAttribute("aria-selected", "true");
  });

  it("renders a selected audio file without calling a backend", () => {
    render(<VieneuPage />);
    fireEvent.click(screen.getByRole("tab", { name: /clone voice/i }));
    const input = screen.getByLabelText(/voice sample file/i) as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], "sample.wav", { type: "audio/wav" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText("sample.wav")).toBeInTheDocument();
    expect(screen.getByText(/analysis pending/i)).toBeInTheDocument();
  });
});
