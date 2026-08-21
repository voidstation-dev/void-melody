// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VoiceSettingsPanel } from "./voice-settings-panel";
import { I18nProvider } from "@/contexts/i18n-provider";
import { Voice, CustomVoice } from "@/types/voice";

const mockPresets: Voice[] = [
  {
    id: "preset-1",
    displayName: "Nhỏ Ngọt Ngào",
    languageCode: "vi-VN",
    languageShort: "vi",
    voiceType: "BV421_vivn_streaming",
    resourceId: "res-1",
    capturedAt: null,
  },
  {
    id: "preset-2",
    displayName: "Giọng Nữ Phổ Thông",
    languageCode: "vi-VN",
    languageShort: "vi",
    voiceType: "BV422_vivn_streaming",
    resourceId: "res-2",
    capturedAt: null,
  },
];

const mockCustomVoices: CustomVoice[] = [
  {
    id: "custom-voice-123",
    display_name: "Giọng Đọc Cá Nhân Của Tôi",
    transcript: "Xin chào các bạn",
    consent_given: true,
    created_at: "2026-08-21T00:00:00Z",
    provider_id: "vieneu",
    engine_id: "v3turbo",
    status: "ready",
    quality_score: 96,
    reference_duration_seconds: 5.2,
    consent_version: "v1",
  },
];

function renderPanel(props: Partial<React.ComponentProps<typeof VoiceSettingsPanel>> = {}) {
  const defaultProps = {
    voices: mockPresets,
    customVoices: mockCustomVoices,
    selectedVoice: "BV421_vivn_streaming",
    onSelectVoice: vi.fn(),
    rate: 1.0,
    onRateChange: vi.fn(),
  };

  return render(
    <I18nProvider initialLocale="vi">
      <VoiceSettingsPanel {...defaultProps} {...props} />
    </I18nProvider>
  );
}

describe("VoiceSettingsPanel", () => {
  it("renders selected preset voice information", () => {
    renderPanel({ selectedVoice: "BV421_vivn_streaming" });

    expect(screen.getByText("Nhỏ Ngọt Ngào")).toBeInTheDocument();
    expect(screen.getByText(/vi-VN · Giọng mẫu/i)).toBeInTheDocument();
  });

  it("renders selected custom cloned voice with Clone badge", () => {
    renderPanel({ selectedVoice: "custom-voice-123" });

    expect(screen.getByText("Giọng Đọc Cá Nhân Của Tôi")).toBeInTheDocument();
    expect(screen.getByText("Clone")).toBeInTheDocument();
    expect(screen.getByText(/VieNeu · 96\/100 · Giọng đã nhân bản/i)).toBeInTheDocument();
  });

  it("opens dropdown and lists both custom and preset voices with filter tabs", () => {
    renderPanel();

    const trigger = screen.getByText("Nhỏ Ngọt Ngào");
    fireEvent.click(trigger);

    // Filter tabs visible
    expect(screen.getByRole("button", { name: /Tất cả \(3\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mẫu có sẵn \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Giọng của tôi \(1\)/i })).toBeInTheDocument();

    // Both sections present
    expect(screen.getByText("Giọng của tôi (Clone)")).toBeInTheDocument();
    expect(screen.getByText("Giọng mẫu có sẵn")).toBeInTheDocument();
    expect(screen.getByText("Giọng Đọc Cá Nhân Của Tôi")).toBeInTheDocument();
    expect(screen.getByText("Giọng Nữ Phổ Thông")).toBeInTheDocument();
  });

  it("selects a custom cloned voice on click", () => {
    const onSelectVoice = vi.fn();
    renderPanel({ onSelectVoice });

    fireEvent.click(screen.getByText("Nhỏ Ngọt Ngào"));
    const customVoiceOption = screen.getByText("Giọng Đọc Cá Nhân Của Tôi");
    fireEvent.click(customVoiceOption);

    expect(onSelectVoice).toHaveBeenCalledWith("custom-voice-123");
  });

  it("filters voices by search input", () => {
    renderPanel();

    fireEvent.click(screen.getByText("Nhỏ Ngọt Ngào"));
    const searchInput = screen.getByPlaceholderText(/Tìm kiếm giọng đọc/i);
    fireEvent.change(searchInput, { target: { value: "Cá Nhân" } });

    expect(screen.getByText("Giọng Đọc Cá Nhân Của Tôi")).toBeInTheDocument();
    expect(screen.queryByText("Giọng Nữ Phổ Thông")).not.toBeInTheDocument();
  });
});
