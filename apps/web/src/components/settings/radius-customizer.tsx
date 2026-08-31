import React from "react"
import { useThemePalette } from "@/contexts/theme-palette-provider"
import { useTranslation } from "@/hooks/use-translation"
import { SlidersHorizontal } from "lucide-react"

const RADIUS_PRESETS = [
  { value: 0.25, label: "0.25rem", nameVi: "Sắc nét", nameEn: "Sharp" },
  { value: 0.5, label: "0.5rem", nameVi: "Vừa", nameEn: "Medium" },
  { value: 0.75, label: "0.75rem", nameVi: "Mặc định", nameEn: "Default" },
  { value: 1.0, label: "1.0rem", nameVi: "Tròn", nameEn: "Rounded" },
  { value: 1.25, label: "1.25rem", nameVi: "Mềm mại", nameEn: "Soft" },
]

export function RadiusCustomizer() {
  const { radius, setRadius } = useThemePalette()
  const { locale } = useTranslation()
  const isVi = locale === "vi"

  return (
    <div className="pt-2 border-t border-border/50">
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-primary" />
          <span className="text-xs sm:text-sm font-bold text-foreground">
            {isVi ? "Độ bo góc (Corner Radius)" : "Corner Radius"}
          </span>
        </div>
        <span className="text-xs font-mono font-bold text-muted-foreground bg-muted/80 px-2 py-0.5 rounded-md border border-border/40">
          {radius.toFixed(2)}rem
        </span>
      </div>

      {/* Preset Pills */}
      <div className="grid grid-cols-5 gap-1.5">
        {RADIUS_PRESETS.map((preset) => {
          const isSelected = Math.abs(radius - preset.value) < 0.05
          return (
            <button
              key={preset.value}
              type="button"
              onClick={() => setRadius(preset.value)}
              className={`flex flex-col items-center justify-center p-2 rounded-xl border text-center transition-all cursor-pointer ${
                isSelected
                  ? "border-primary bg-primary/10 text-primary font-bold shadow-2xs ring-1 ring-primary/30"
                  : "border-border/60 bg-background/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <span className="text-xs font-bold">{preset.label}</span>
              <span className="text-[10px] text-muted-foreground mt-0.5">
                {isVi ? preset.nameVi : preset.nameEn}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
