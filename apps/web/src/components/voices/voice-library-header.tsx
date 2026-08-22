"use client"

import Link from "next/link"
import { ChevronDown, Plus, Search } from "lucide-react"
import { useTranslation } from "@/hooks/use-translation"

type FilterOption = { value: string; label: string }

type VoiceLibraryHeaderProps = {
  search: string
  provider: string
  language: string
  providers: FilterOption[]
  languages: FilterOption[]
  onSearchChange: (value: string) => void
  onProviderChange: (value: string) => void
  onLanguageChange: (value: string) => void
}

function FilterSelect({ id, label, value, options, onChange }: { id: string; label: string; value: string; options: FilterOption[]; onChange: (value: string) => void }) {
  return (
    <label className="relative flex min-w-[150px] flex-1 items-center">
      <span className="sr-only">{label}</span>
      <select
        id={id}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-11 w-full appearance-none rounded-xl border border-border bg-card px-3.5 pr-9 text-sm font-semibold text-foreground outline-none transition-colors hover:border-primary/30 focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/30"
      >
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 h-4 w-4 text-muted-foreground" />
    </label>
  )
}

export function VoiceLibraryHeader({ search, provider, language, providers, languages, onSearchChange, onProviderChange, onLanguageChange }: VoiceLibraryHeaderProps) {
  const { t } = useTranslation()

  return (
    <header className="shrink-0 space-y-5">
      <div>
        <p className="text-[11px] font-extrabold uppercase tracking-[0.2em] text-primary/70">Melody / Voice Library</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-foreground sm:text-4xl">{t("voices.title")}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t("voices.subtitle")}</p>
      </div>

      <div className="flex flex-col gap-2.5 xl:flex-row">
        <label className="relative min-w-0 flex-[2]">
          <span className="sr-only">{t("voices.searchLabel")}</span>
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            id="voice-library-search"
            type="search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={t("voices.searchPlaceholder")}
            className="min-h-11 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm font-medium outline-none transition-colors placeholder:text-muted-foreground/70 hover:border-primary/30 focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/30"
          />
        </label>
        <div className="flex flex-col gap-2.5 sm:flex-row xl:flex-1">
          <FilterSelect id="voice-library-provider" label={t("voices.providerFilter")} value={provider} options={providers} onChange={onProviderChange} />
          <FilterSelect id="voice-library-language" label={t("voices.languageFilter")} value={language} options={languages} onChange={onLanguageChange} />
        </div>
        <Link
          href="/vieneu"
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-primary-foreground shadow-2xs transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <Plus className="h-4 w-4" />
          {t("voices.newVoice")}
        </Link>
      </div>
    </header>
  )
}
