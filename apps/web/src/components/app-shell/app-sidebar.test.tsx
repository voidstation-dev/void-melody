// @vitest-environment jsdom

import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { AppSidebar } from "./app-sidebar"
import { I18nProvider } from "@/contexts/i18n-provider"

// Keep the test focused on nav structure: stub version fetch.
vi.mock("@/lib/runtime-version", () => ({
  getRuntimeVersion: () => Promise.resolve("0.0.0-test"),
}))
import { vi } from "vitest"

describe("AppSidebar VoxCPM2 entry", () => {
  it("has a VoxCPM2 Studio link in the create group", () => {
    render(
      <I18nProvider>
        <AppSidebar />
      </I18nProvider>,
    )
    const link = screen.getByRole("link", { name: /VoxCPM2 Studio/ })
    expect(link).toHaveAttribute("href", "/voxcpm")
  })

  it("keeps existing create-group entries", () => {
    render(
      <I18nProvider>
        <AppSidebar />
      </I18nProvider>,
    )
    expect(screen.getByRole("link", { name: /Tạo audio/ })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Phòng thu giọng/ })).toBeInTheDocument()
  })
})