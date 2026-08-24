import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import { TTSStudio } from "@/components/tts/tts-studio"

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
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading Studio…</div>}>
      <TTSStudio />
    </Suspense>
  )
}
