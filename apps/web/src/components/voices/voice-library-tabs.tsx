"use client"

import { VoiceLibraryTab } from "./voice-library-utils"

type VoiceLibraryTabsProps = { activeTab: VoiceLibraryTab; counts: Record<VoiceLibraryTab, number>; labels: Record<VoiceLibraryTab, string>; ariaLabel: string; onChange: (tab: VoiceLibraryTab) => void }

export function VoiceLibraryTabs({ activeTab, counts, labels, ariaLabel, onChange }: VoiceLibraryTabsProps) {
  return (
    <div role="tablist" aria-label={ariaLabel} className="inline-flex w-fit max-w-full flex-wrap rounded-xl border border-border bg-card p-1 shadow-xs">
      {(["all", "preset", "custom"] as const).map((tab) => (
        <button
          key={tab}
          type="button"
          role="tab"
          aria-selected={activeTab === tab}
          tabIndex={activeTab === tab ? 0 : -1}
          onClick={() => onChange(tab)}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
              const index = ["all", "preset", "custom"].indexOf(tab)
              const nextIndex = event.key === "ArrowRight" ? (index + 1) % 3 : (index + 2) % 3
              onChange(["all", "preset", "custom"][nextIndex] as VoiceLibraryTab)
            }
          }}
          className={`inline-flex min-h-9 items-center gap-2 rounded-lg px-3.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${activeTab === tab ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
        >
          <span>{labels[tab]}</span>
          <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${activeTab === tab ? "bg-primary-foreground/15 text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{counts[tab]}</span>
        </button>
      ))}
    </div>
  )
}
