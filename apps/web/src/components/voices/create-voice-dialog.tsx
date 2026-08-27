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

  function handleDesign() {
    onClose()
    navigate({ to: "/voice-design" })
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
            onClick={handleDesign}
            className="group flex w-full items-center gap-4 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-left transition-colors hover:bg-amber-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-foreground">{t("voices.voiceDesignCard")}</p>
              <p className="text-[11px] text-muted-foreground">{t("voices.voiceDesignCardDesc")}</p>
            </div>
            <span className="shrink-0 text-[11px] text-muted-foreground">{t("voices.voiceDesignCardEta")}</span>
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
