import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Gauge } from "lucide-react"
import { useTranslation } from "@/hooks/use-translation"

interface SpeedControlProps {
  speed: number
  onChange: (value: number) => void
  disabled?: boolean
}

export function SpeedControl({ speed, onChange, disabled }: SpeedControlProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
          <Gauge className="h-3.5 w-3.5 text-muted-foreground" />
          <span>{t("audioStudio.speedLabel")}</span>
        </div>
        <Badge variant="secondary" className="font-mono text-xs font-bold">
          {speed.toFixed(2)}x
        </Badge>
      </div>

      <Slider
        min={0.5}
        max={2.0}
        step={0.05}
        value={[speed]}
        onValueChange={(vals) => {
          if (vals[0] !== undefined) onChange(vals[0])
        }}
        disabled={disabled}
        className="py-1"
      />

      <div className="flex items-center justify-between text-[10px] font-bold tracking-wider text-muted-foreground/70 uppercase">
        <span>{t("audioStudio.speedSlow")}</span>
        <span>{t("audioStudio.speedNormal")}</span>
        <span>{t("audioStudio.speedFast")}</span>
      </div>
    </div>
  )
}
