// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nProvider } from "@/contexts/i18n-provider"
import VoicesPage from "./page"

vi.mock("@/components/app-shell/page-container", () => ({
  PageContainer: ({ children }: { children: React.ReactNode }) => <main>{children}</main>,
}))

vi.mock("@/hooks/use-voices", () => ({
  useVoices: vi.fn(() => ({
    data: {
      items: [{
        id: "preset-1",
        languageCode: "vi-VN",
        languageShort: "vi",
        voiceType: "BV421_vivn_streaming",
        displayName: "Nhỏ Ngọt Ngào",
        resourceId: "resource-1",
        capturedAt: null,
        providerId: "capcut",
      }],
      total: 1,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}))

vi.mock("@/hooks/use-custom-voices", () => ({
  useCustomVoices: vi.fn(() => ({
    data: {
      items: [{
        id: "custom-1",
        display_name: "Adam",
        transcript: "Xin chào",
        consent_given: true,
        created_at: "2026-08-21T00:00:00Z",
        provider_id: "vieneu",
        engine_id: "v3turbo",
        status: "ready",
        reference_duration_seconds: 6,
        consent_version: "voice-lab-v1",
      }],
      total: 1,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}))

vi.mock("@/components/voices/voice-preview-button", () => ({
  VoicePreviewButton: () => <button type="button">Nghe thử</button>,
}))

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <I18nProvider initialLocale="vi">
        <VoicesPage />
      </I18nProvider>
    </QueryClientProvider>,
  )
}

describe("VoicesPage", () => {
  it("keeps preset/custom tabs and filters real provider data", () => {
    renderPage()

    expect(screen.getByText("Nhỏ Ngọt Ngào")).toBeInTheDocument()
    expect(screen.getByText("Adam")).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Nhà cung cấp" })).toBeInTheDocument()

    fireEvent.change(screen.getByRole("combobox", { name: "Nhà cung cấp" }), { target: { value: "capcut" } })
    expect(screen.getByText("Nhỏ Ngọt Ngào")).toBeInTheDocument()
    expect(screen.queryByText("Adam")).not.toBeInTheDocument()

    fireEvent.change(screen.getByRole("combobox", { name: "Nhà cung cấp" }), { target: { value: "all" } })
    fireEvent.click(screen.getByRole("tab", { name: /giọng của tôi/i }))
    expect(screen.getByText("Adam")).toBeInTheDocument()
    expect(screen.queryByText("Nhỏ Ngọt Ngào")).not.toBeInTheDocument()
  })
})
