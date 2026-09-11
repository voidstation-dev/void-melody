// @vitest-environment jsdom
//
// The global test setup mocks @tanstack/react-router, so building a real router
// instance here is not possible. The route test asserts the route module shape;
// full rendering is covered by voxcpm-page.test.tsx.

import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { Route as VoxCpmRoute } from "./voxcpm"
import { I18nProvider } from "@/contexts/i18n-provider"

describe("voxcpm route", () => {
  it("is registered in the generated route tree as /voxcpm", async () => {
    // The generated route tree maps the module id '/voxcpm' to this file.
    const tree = await import("../routeTree.gen")
    const children = ((tree as any).routeTree.children ?? []) as Array<{
      options?: { path?: string }
    }>
    expect(children.map((r) => r.options?.path)).toContain("/voxcpm")
  })

  it("renders the VoxCPM2 page shell", () => {
    const Component = VoxCpmRoute.options.component!
    render(
      <I18nProvider>
        <Component />
      </I18nProvider>,
    )
    expect(screen.getByText("VoxCPM2 Studio")).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Clone giọng" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "TTS cảm xúc" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Giọng đã clone" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Runtime" })).toBeInTheDocument()
  })
})