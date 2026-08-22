"use client"

import Link from "next/link"
import { Plus, RefreshCcw } from "lucide-react"
import { CustomVoice } from "@/types/voice"
import { useTranslation } from "@/hooks/use-translation"
import { CustomVoiceCard } from "./custom-voice-card"
import { VoiceLibraryEmpty } from "./voice-library-empty"
import { VoiceLibrarySkeleton } from "./voice-library-skeleton"

type MyVoicesSectionProps = { voices: CustomVoice[]; total: number; page: number; pageSize: number; isLoading: boolean; isError: boolean; hasFilters: boolean; deletingVoiceId?: string; onRetry: () => void; onDelete: (voiceId: string) => void; onPageChange: (page: number) => void }

export function MyVoicesSection({ voices, total, page, pageSize, isLoading, isError, hasFilters, deletingVoiceId, onRetry, onDelete, onPageChange }: MyVoicesSectionProps) {
  const { t } = useTranslation()
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <section aria-labelledby="my-voices-heading" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h2 id="my-voices-heading" className="text-lg font-black tracking-tight">{t("voices.customHeading")}</h2><p className="mt-1 text-sm text-muted-foreground">{t("voices.customSectionDescription")}</p></div>
        <Link href="/vieneu" className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><Plus className="h-3.5 w-3.5" />{t("voices.newVoice")}</Link>
      </div>
      {isLoading ? <VoiceLibrarySkeleton variant="custom" /> : isError ? <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-5 py-6 text-sm"><p className="font-bold text-destructive">{t("voices.customLoadError")}</p><button type="button" onClick={onRetry} className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-destructive underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><RefreshCcw className="h-3.5 w-3.5" />{t("common.retry")}</button></div> : voices.length === 0 ? <VoiceLibraryEmpty kind={hasFilters ? "search" : "custom"} /> : <div className="grid gap-3 sm:grid-cols-2">{voices.map((voice) => <CustomVoiceCard key={voice.id} voice={voice} onDelete={onDelete} deleting={deletingVoiceId === voice.id} />)}</div>}
      {!isLoading && !isError && total > pageSize && <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground"><span>{t("voices.pageInfo", { current: page, total: totalPages })}</span><div className="flex gap-2"><button type="button" disabled={page === 1} onClick={() => onPageChange(page - 1)} className="rounded-xl border border-border px-3.5 py-2 font-bold hover:bg-muted disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{t("common.previous")}</button><button type="button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)} className="rounded-xl border border-border px-3.5 py-2 font-bold hover:bg-muted disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{t("common.next")}</button></div></div>}
    </section>
  )
}
