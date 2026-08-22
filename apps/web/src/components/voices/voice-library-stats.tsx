import { Library, Mic2, UserRound } from "lucide-react"
import { useTranslation } from "@/hooks/use-translation"

type VoiceLibraryStatsProps = { total: number; preset: number; custom: number }

export function VoiceLibraryStats({ total, preset, custom }: VoiceLibraryStatsProps) {
  const { t } = useTranslation()
  const stats = [
    { label: t("voices.totalVoices"), value: total, icon: Library },
    { label: t("voices.presetCount"), value: preset, icon: Mic2 },
    { label: t("voices.customCount"), value: custom, icon: UserRound },
  ]

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3" aria-label={t("voices.summaryLabel")}>
      {stats.map(({ label, value, icon: Icon }) => (
        <div key={label} className="flex items-center gap-3 rounded-2xl border border-border/70 bg-card px-4 py-3.5 shadow-xs">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-muted text-muted-foreground"><Icon className="h-4 w-4" /></span>
          <div>
            <p className="text-xl font-black leading-none tracking-tight">{value}</p>
            <p className="mt-1 text-[11px] font-bold text-muted-foreground">{label}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
