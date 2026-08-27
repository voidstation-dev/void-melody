import { createFileRoute } from "@tanstack/react-router"
import { useMemo, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { CreateVoiceDialog } from "@/components/voices/create-voice-dialog"
import { VoiceLibraryHeader } from "@/components/voices/voice-library-header"
import { VoiceLibraryStats } from "@/components/voices/voice-library-stats"
import { VoiceLibraryTabs } from "@/components/voices/voice-library-tabs"
import { MyVoicesSection } from "@/components/voices/my-voices-section"
import { PresetVoicesSection } from "@/components/voices/preset-voices-section"
import { useCustomVoices } from "@/hooks/use-custom-voices"
import { useTranslation } from "@/hooks/use-translation"
import { useVoices } from "@/hooks/use-voices"
import { deleteCustomVoice } from "@/api/voices"
import { VoiceLibraryTab, customVoiceAsFilterable, getVoiceLanguages, getVoiceProviders, matchesVoiceFilters } from "@/components/voices/voice-library-utils"
import { voiceQueries } from "@/queries/voices.queries"

const customPageSize = 20

export const Route = createFileRoute("/voices")({
  loader: ({ context }) => {
    void context.queryClient.ensureQueryData(voiceQueries.list())
    void context.queryClient.ensureQueryData(voiceQueries.customList(undefined, 1, customPageSize))
  },
  component: VoicesRoute,
})

function VoicesRoute() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [provider, setProvider] = useState("all")
  const [language, setLanguage] = useState("all")
  const [customPage, setCustomPage] = useState(1)
  const [tab, setTab] = useState<VoiceLibraryTab>("all")
  const [createOpen, setCreateOpen] = useState(false)

  // Presets are a small local catalog; fetching the complete list allows the
  // provider/language filters to work without changing the backend contract.
  const presetQuery = useVoices()
  const customSearch = /vieneu|omnivoice|capcut|clone|vi-vn|en-us/i.test(search) ? undefined : search.trim() || undefined
  const customQuery = useCustomVoices(customSearch, customPage, customPageSize)
  const deleteVoice = useMutation({
    mutationFn: deleteCustomVoice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["custom-voices"] }),
  })

  const presetVoices = useMemo(() => presetQuery.data?.items ?? [], [presetQuery.data?.items])
  const customVoices = useMemo(() => customQuery.data?.items ?? [], [customQuery.data?.items])
  const presetProviders = getVoiceProviders(presetVoices)
  const customProviders = Array.from(new Set(customVoices.map((voice) => voice.provider_id).filter(Boolean))) as string[]
  const providers = Array.from(new Set([...presetProviders, ...customProviders])).sort()
  const languages = getVoiceLanguages(presetVoices)

  const filteredPresetVoices = useMemo(
    () => presetVoices.filter((voice) => matchesVoiceFilters(voice, search, provider, language)),
    [presetVoices, search, provider, language],
  )
  const filteredCustomVoices = useMemo(
    () => customVoices.filter((voice) => matchesVoiceFilters(customVoiceAsFilterable(voice), search, provider, language)),
    [customVoices, search, provider, language],
  )

  const hasFilters = Boolean(search.trim() || provider !== "all" || language !== "all")
  const showPreset = tab !== "custom"
  const showCustom = tab !== "preset"
  const presetCount = presetQuery.data?.total ?? presetVoices.length
  const customCount = customQuery.data?.total ?? customVoices.length

  const resetSearch = () => {
    setSearch("")
    setProvider("all")
    setLanguage("all")
    setCustomPage(1)
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col gap-6 overflow-hidden">
      <div className="shrink-0 space-y-6">
        <VoiceLibraryHeader
          search={search}
          provider={provider}
          language={language}
          providers={[{ value: "all", label: t("voices.allProviders") }, ...providers.map((value) => ({ value, label: value === "vieneu" ? "VieNeu" : value === "omnivoice" ? "OmniVoice" : value === "capcut" ? "CapCut" : value }))]}
          languages={[{ value: "all", label: t("voices.allLanguages") }, ...languages.map((value) => ({ value, label: value }))]}
          onSearchChange={(value) => { setSearch(value); setCustomPage(1) }}
          onProviderChange={(value) => { setProvider(value); setCustomPage(1) }}
          onLanguageChange={(value) => { setLanguage(value); setCustomPage(1) }}
        />

        <VoiceLibraryStats total={presetCount + customCount} preset={presetCount} custom={customCount} />

        <VoiceLibraryTabs
          activeTab={tab}
          counts={{ all: presetCount + customCount, preset: presetCount, custom: customCount }}
          labels={{ all: t("voices.tabAll"), preset: t("voices.tabPreset"), custom: t("voices.tabCustom") }}
          ariaLabel={t("voices.tabsLabel")}
          onChange={setTab}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-2 pb-6">
        <div className="space-y-10">
          {showCustom && (
            <MyVoicesSection
              voices={filteredCustomVoices}
              total={customCount}
              page={customPage}
              pageSize={customPageSize}
              isLoading={customQuery.isLoading}
              isError={customQuery.isError}
              hasFilters={hasFilters}
              deletingVoiceId={deleteVoice.isPending ? deleteVoice.variables : undefined}
              onRetry={() => void customQuery.refetch()}
              onDelete={(voiceId) => deleteVoice.mutate(voiceId)}
              onPageChange={setCustomPage}
              onCreateVoice={() => setCreateOpen(true)}
            />
          )}

          <CreateVoiceDialog open={createOpen} onClose={() => setCreateOpen(false)} />

          {showPreset && (
            <PresetVoicesSection
              voices={filteredPresetVoices}
              isLoading={presetQuery.isLoading}
              isError={presetQuery.isError}
              hasFilters={hasFilters}
              onRetry={() => void presetQuery.refetch()}
            />
          )}

          {hasFilters && filteredCustomVoices.length === 0 && filteredPresetVoices.length === 0 && !customQuery.isLoading && !presetQuery.isLoading && (
            <button type="button" onClick={resetSearch} className="mx-auto block text-xs font-bold text-primary underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{t("voices.clearFilters")}</button>
          )}
        </div>
      </div>
    </div>
  )
}
