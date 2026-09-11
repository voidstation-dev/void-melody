import * as React from "react"
import { useNavigate } from "@tanstack/react-router"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { useTranslation } from "@/hooks/use-translation"
import { Sparkles, Zap, Clock } from "lucide-react"

type CreateVoiceDialogProps = {
  open: boolean
  onClose: () => void
}

export function CreateVoiceDialog({ open, onClose }: CreateVoiceDialogProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  function handleVoxCpm() {
    onClose()
    navigate({ to: "/voxcpm" })
  }

  function handleClone() {
    onClose()
    navigate({ to: "/vieneu" })
  }

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="sm:max-w-md" showCloseButton>
        <DialogHeader>
          <DialogTitle>{t("voices.createVoiceTitle")}</DialogTitle>
          <DialogDescription>{t("voices.createVoiceSubtitle")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3 pt-1">
          <button
            type="button"
            onClick={handleVoxCpm}
            className="group flex w-full items-center gap-4 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 text-left transition-colors hover:bg-indigo-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-500/15 text-indigo-600 dark:text-indigo-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-foreground">VoxCPM2 Instant Clone</p>
              <p className="text-[11px] text-muted-foreground">Clone giọng 48kHz chất lượng cao từ file mẫu ngắn</p>
            </div>
            <span className="shrink-0 text-[11px] text-muted-foreground">~5-10s</span>
          </button>

          <button
            type="button"
            onClick={handleClone}
            className="group flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Zap className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-foreground">{t("voices.instantCloneCard")}</p>
              <p className="text-[11px] text-muted-foreground">{t("voices.instantCloneCardDesc")}</p>
            </div>
            <span className="shrink-0 text-[11px] text-muted-foreground">{t("voices.instantCloneCardEta")}</span>
          </button>

          <button
            type="button"
            disabled
            className="group flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left opacity-60"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <Clock className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-foreground">{t("voices.professionalCloneCard")}</p>
              <p className="text-[11px] text-muted-foreground">{t("voices.professionalCloneCardDesc")}</p>
            </div>
            <span className="shrink-0 text-[11px] text-muted-foreground">{t("voices.comingSoonBadge")}</span>
          </button>

          <button
            type="button"
            disabled
            className="group flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left opacity-60"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-foreground">{t("voices.voiceRemixCard")}</p>
              <p className="text-[11px] text-muted-foreground">{t("voices.voiceRemixCardDesc")}</p>
            </div>
            <span className="shrink-0 text-[11px] text-muted-foreground">{t("voices.comingSoonBadge")}</span>
          </button>
        </div>

        <div className="flex justify-end pt-1">
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
