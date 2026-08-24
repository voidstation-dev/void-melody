import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import { VieneuPage } from "@/components/vieneu/vieneu-page"

type VieneuSearchParams = {
  voice?: string
}

export const Route = createFileRoute("/vieneu")({
  validateSearch: (search: Record<string, unknown>): VieneuSearchParams => {
    return {
      voice: typeof search.voice === "string" ? search.voice : undefined,
    }
  },
  component: VieneuRouteComponent,
})

function VieneuRouteComponent() {
  const { voice } = Route.useSearch()
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading Voice Lab…</div>}>
      <VieneuPage initialVoiceId={voice} />
    </Suspense>
  )
}
