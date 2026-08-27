type VoiceWaveformProps = {
  accent?: "coral" | "muted" | "amber"
}

const BAR_HEIGHTS = [8, 14, 23, 12, 17, 10, 26, 15, 9, 13, 12, 8, 20, 10, 15, 24, 12, 18, 9, 13, 22, 11, 16, 8]

export function VoiceWaveform({ accent = "muted" }: VoiceWaveformProps) {
  return (
    <span data-testid="voice-waveform" aria-hidden="true" className="inline-flex h-8 items-center gap-[3px]">
      {BAR_HEIGHTS.map((height, index) => (
        <span
          key={`${height}-${index}`}
          data-testid="voice-waveform-bar"
          className="w-[3px] rounded-full"
          style={{
            height,
            backgroundColor:
              index % 5 === 0
                ? accent === "coral"
                  ? "#df604e"
                  : accent === "amber"
                    ? "#f59e0b"
                    : "#d7d6d3"
                : "#d7d6d3",
          }}
        />
      ))}
    </span>
  )
}
