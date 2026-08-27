import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import { VoiceDesignModal } from "@/components/voice-design/voice-design-modal"
import { useTranslation } from "@/hooks/use-translation"

export const Route = createFileRoute("/voice-design")({
  component: VoiceDesignRouteComponent,
})

function VoiceDesignRouteComponent() {
  const { t } = useTranslation()
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">{t("common.loadingVoiceLab")}</div>}>
      <div className="flex h-full min-h-0 flex-1 flex-col p-6">
        <VoiceDesignModal open onClose={() => window.history.back()} />
      </div>
    </Suspense>
  )
}
