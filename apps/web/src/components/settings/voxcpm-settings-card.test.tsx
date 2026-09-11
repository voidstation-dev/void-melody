// @vitest-environment jsdom

import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { I18nProvider } from "@/contexts/i18n-provider"
import type { VoxCpmInstallationInfo } from "@/api/voxcpm"

const installationFixture: VoxCpmInstallationInfo = {
  provider_id: "voxcpm2",
  model_id: "openbmb/VoxCPM2",
  env_present: true,
  package_installed: true,
  model_status: "downloaded",
  model_snapshot: "/snapshots/abc",
  downloaded_bytes: 4_600_000_000,
  storage_dir: "~/.cache/huggingface",
  sample_rate: 48000,
  device_policy: "auto",
}

export const mocks = {
  fetchVoxCpmInstallation: vi.fn().mockResolvedValue(installationFixture),
  installVoxCpmRuntime: vi.fn().mockResolvedValue(undefined),
  verifyVoxCpmInstallation: vi
    .fn()
    .mockResolvedValue({ ok: true, version: "0.2.5", error: null }),
  removeVoxCpmEnv: vi.fn().mockResolvedValue(undefined),
  removeVoxCpmModel: vi.fn().mockResolvedValue(undefined),
}

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/api/voxcpm", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/voxcpm")>()
  return {
    ...actual,
    fetchVoxCpmInstallation: mocks.fetchVoxCpmInstallation,
    installVoxCpmRuntime: mocks.installVoxCpmRuntime,
    verifyVoxCpmInstallation: mocks.verifyVoxCpmInstallation,
    removeVoxCpmEnv: mocks.removeVoxCpmEnv,
    removeVoxCpmModel: mocks.removeVoxCpmModel,
  }
})

const { VoxCpmSettingsCard } = await import("./voxcpm-settings-card")

function renderCard() {
  return render(
    <I18nProvider>
      <VoxCpmSettingsCard />
    </I18nProvider>,
  )
}

describe("VoxCpmSettingsCard", () => {
  beforeEach(() => {
    mocks.fetchVoxCpmInstallation.mockResolvedValue(installationFixture)
    mocks.verifyVoxCpmInstallation.mockResolvedValue({
      ok: true,
      version: "0.2.5",
      error: null,
    })
  })

  it("shows installation snapshot with model id and storage", async () => {
    renderCard()
    await waitFor(() => {
      expect(screen.getByText("openbmb/VoxCPM2")).toBeInTheDocument()
    })
    expect(screen.getByText(/4\.3 GB/)).toBeInTheDocument()
  })

  it("hides install button when installed, shows remove actions", async () => {
    renderCard()
    await waitFor(() => {
      expect(screen.getByText("Sẵn sàng")).toBeInTheDocument()
    })
    expect(screen.queryByText("Cài đặt runtime")).not.toBeInTheDocument()
    expect(screen.getByText("Gỡ runtime")).toBeInTheDocument()
    expect(screen.getByText("Xóa model")).toBeInTheDocument()
  })

  it("shows install button when runtime is missing", async () => {
    mocks.fetchVoxCpmInstallation.mockResolvedValue({
      ...installationFixture,
      package_installed: false,
      model_status: "not_downloaded",
      downloaded_bytes: 0,
    })
    renderCard()
    await waitFor(() => {
      expect(screen.getByText("Chưa cài đặt")).toBeInTheDocument()
    })
    expect(screen.getByText("Cài đặt runtime")).toBeInTheDocument()
    expect(screen.queryByText("Xóa model")).not.toBeInTheDocument()
  })
})