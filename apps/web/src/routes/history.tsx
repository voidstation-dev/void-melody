import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useTranslation } from "@/hooks/use-translation"
import { JobQueueSidebar } from "@/components/tts/job-queue-sidebar"
import { historyQueries } from "@/queries/history.queries"
import { toast } from "sonner"

export const Route = createFileRoute("/history")({
  loader: ({ context }) => {
    void context.queryClient.ensureQueryData(historyQueries.list(1))
  },
  component: HistoryRoute,
})

function HistoryRoute() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const handleReparse = (jobText: string) => {
    try {
      const existing = localStorage.getItem("voidmelody_audio_studio_draft_v1")
      const draft = existing ? JSON.parse(existing) : {}
      localStorage.setItem(
        "voidmelody_audio_studio_draft_v1",
        JSON.stringify({
          ...draft,
          text: jobText,
          updatedAt: Date.now(),
        }),
      )
    } catch {
      // ignore
    }
    toast.success(t("history.reloadedToStudioToast"))
    void navigate({ to: "/" })
  }

  return (
    <div className="flex flex-col h-full space-y-4 max-w-[1400px] mx-auto w-full pb-8">
      <div className="shrink-0">
        <h1 className="text-xl sm:text-2xl font-black tracking-tight text-foreground">{t("history.title")}</h1>
        <p className="text-xs text-muted-foreground mt-0.5">{t("history.subtitle")}</p>
      </div>

      <div className="flex-1 min-h-0">
        <JobQueueSidebar
          onReparse={handleReparse}
          title={t("history.title")}
          maxHeightClass="max-h-[calc(100vh-220px)] min-h-[400px]"
          className="h-full border border-border/80 shadow-xs"
        />
      </div>
    </div>
  )
}
