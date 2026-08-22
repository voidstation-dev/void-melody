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
})
