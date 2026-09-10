import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import { VoxCpmPage } from "@/components/voxcpm/voxcpm-page"
import { useTranslation } from "@/hooks/use-translation"

type VoxCpmSearch = {
  voice?: string
}

export const Route = createFileRoute("/voxcpm")({
  validateSearch: (search: Record<string, unknown>): VoxCpmSearch => {
    return {
      voice: typeof search.voice === "string" ? search.voice : undefined,
    }
  },
  component: VoxCpmRouteComponent,
})

function VoxCpmRouteComponent() {
  const { t } = useTranslation()
  return (
    <Suspense
      fallback={<div className="p-6 text-sm text-muted-foreground">{t("common.loading")}</div>}
    >
      <VoxCpmPage />
    </Suspense>
  )
}