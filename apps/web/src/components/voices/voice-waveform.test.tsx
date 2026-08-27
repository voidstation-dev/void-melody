// @vitest-environment jsdom

import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { VoiceWaveform } from "./voice-waveform"

describe("VoiceWaveform", () => {
  it("renders an aria-hidden decorative waveform with stable bars", () => {
    render(<VoiceWaveform />)

    expect(screen.getByTestId("voice-waveform")).toHaveAttribute("aria-hidden", "true")
    expect(screen.getAllByTestId("voice-waveform-bar")).toHaveLength(24)
  })

  it("supports the amber accent used by OmniVoice design cards", () => {
    render(<VoiceWaveform accent="amber" />)

    const bars = screen.getAllByTestId("voice-waveform-bar")
    expect(bars[0]).toHaveStyle({ backgroundColor: "#f59e0b" })
    expect(bars[1]).toHaveStyle({ backgroundColor: "#d7d6d3" })
  })
})
