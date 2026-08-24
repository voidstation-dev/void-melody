import { Radio } from "lucide-react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useTranslation } from "@/hooks/use-translation"

interface OutputFormatProps {
  format: "mp3" | "wav"
  onChange: (format: "mp3" | "wav") => void
  disabled?: boolean
}

export function OutputFormat({ format, onChange, disabled }: OutputFormatProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
          <Radio className="h-3.5 w-3.5 text-muted-foreground" />
          <span>{t("audioStudio.formatLabel")}</span>
        </div>
        <span className="text-[11px] font-medium text-muted-foreground">{t("audioStudio.formatResolution")}</span>
      </div>

      <ToggleGroup
        type="single"
        value={format}
        onValueChange={(val) => {
          if (val === "mp3" || val === "wav") onChange(val)
        }}
        disabled={disabled}
        className="w-full grid grid-cols-2"
      >
        <ToggleGroupItem value="mp3" className="w-full font-bold">
          {t("audioStudio.formatMp3")}
        </ToggleGroupItem>
        <ToggleGroupItem value="wav" className="w-full font-bold">
          {t("audioStudio.formatWav")}
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}
