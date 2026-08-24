import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import { AudioStudioPage } from "@/features/audio-studio"
import { useTranslation } from "@/hooks/use-translation"

type IndexSearch = {
  voice?: string
}

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): IndexSearch => {
    return {
      voice: typeof search.voice === "string" ? search.voice : undefined,
    }
  },
  component: IndexPage,
})

function IndexPage() {
  const { t } = useTranslation()
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">{t("common.loadingAudioStudio")}</div>}>
      <AudioStudioPage />
    </Suspense>
  )
}
