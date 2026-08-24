import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import { AudioStudioPage } from "@/features/audio-studio"

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
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Đang tải Audio Studio…</div>}>
      <AudioStudioPage />
    </Suspense>
  )
}
