import { Mic2, SearchX } from "lucide-react"
import { Link } from "@tanstack/react-router"
import { useTranslation } from "@/hooks/use-translation"

type EmptyKind = "custom" | "preset" | "search"

export function VoiceLibraryEmpty({ kind }: { kind: EmptyKind }) {
  const { t } = useTranslation()
  if (kind === "search") {
    return <div className="rounded-2xl border border-dashed border-border bg-card/60 px-6 py-10 text-center"><SearchX className="mx-auto h-7 w-7 text-muted-foreground" /><h3 className="mt-3 font-bold">{t("voices.noResultsTitle")}</h3><p className="mt-1 text-sm text-muted-foreground">{t("voices.noResultsDescription")}</p></div>
  }
  if (kind === "preset") {
    return <div className="rounded-2xl border border-dashed border-border bg-card/60 px-6 py-10 text-center"><Mic2 className="mx-auto h-7 w-7 text-muted-foreground" /><h3 className="mt-3 font-bold">{t("voices.presetEmpty")}</h3></div>
  }
  return (
    <div className="rounded-2xl border border-dashed border-border bg-card/60 px-6 py-10 text-center">
      <Mic2 className="mx-auto h-7 w-7 text-muted-foreground" />
      <h3 className="mt-3 font-bold">{t("voices.customEmptyTitle")}</h3>
      <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{t("voices.customEmptyDescription")}</p>
      <Link to="/vieneu" className="mt-5 inline-flex min-h-9 items-center rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{t("voices.createFirstVoice")}</Link>
    </div>
  )
}
