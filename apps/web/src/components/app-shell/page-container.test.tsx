// @vitest-environment jsdom

import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { PageContainer } from "./page-container"

vi.mock("./app-header", () => ({ AppHeader: () => <header data-testid="app-header" /> }))
vi.mock("./app-sidebar", () => ({ AppSidebar: () => <aside data-testid="app-sidebar" /> }))

describe("PageContainer", () => {
  it("allows page content to shrink so its own scroll region can consume the viewport", () => {
    render(
      <PageContainer>
        <div>page content</div>
      </PageContainer>,
    )

    const main = screen.getByRole("main")
    expect(main).toHaveClass("min-h-0")
    expect(main).toHaveClass("min-w-0")
    expect(main.parentElement).toHaveClass("min-h-0")
    expect(main.parentElement?.parentElement).toHaveClass("h-dvh")
  })
})
