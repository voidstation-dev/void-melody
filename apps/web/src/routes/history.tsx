import { createFileRoute } from "@tanstack/react-router"
import { useHistory } from "@/hooks/use-history"
import { useTranslation } from "@/hooks/use-translation"

import { historyQueries } from "@/queries/history.queries"

export const Route = createFileRoute("/history")({
  loader: ({ context }) => {
    void context.queryClient.ensureQueryData(historyQueries.list(1))
  },
  component: HistoryRoute,
})

function HistoryRoute() {
  const { data, isLoading } = useHistory()
  const { t } = useTranslation()

  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return t("history.statusCompleted");
      case "failed":
        return t("history.statusFailed");
      case "processing":
        return t("history.statusProcessing");
      case "queued":
        return t("history.statusQueued");
      default:
        return status;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-6 shrink-0">
        <h1 className="text-2xl font-bold">{t("history.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("history.subtitle")}</p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 pr-2 pb-6">
        {isLoading ? (
          <div className="text-sm text-muted-foreground">{t("history.loading")}</div>
        ) : !data?.items || data.items.length === 0 ? (
          <div className="flex min-h-48 items-center justify-center rounded-2xl border border-dashed border-border bg-card p-8 text-center text-muted-foreground">
            <div>
              <p className="font-bold text-foreground">{t("history.empty")}</p>
              <p className="mt-1 text-xs">{t("history.emptyDesc")}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {data.items.map((job) => (
              <div key={job.id} className="flex items-center justify-between rounded-2xl border border-border bg-card p-4 shadow-sm">
                <div>
                  <div className="font-bold text-foreground">{job.voiceDisplayName || job.voiceType}</div>
                  <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{job.textPreview}</div>
                </div>
                <div className="text-xs font-semibold px-2.5 py-1 rounded-full bg-muted text-foreground">
                  {getStatusText(job.status)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
