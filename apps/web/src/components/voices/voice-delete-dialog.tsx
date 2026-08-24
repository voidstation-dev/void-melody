import { AlertTriangle, Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "@/hooks/use-translation"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

type VoiceDeleteDialogProps = {
  open: boolean
  voiceName: string
  pending?: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function VoiceDeleteDialog({
  open,
  voiceName,
  pending = false,
  onCancel,
  onConfirm,
}: VoiceDeleteDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen && !pending) onCancel() }}>
      <DialogContent
        role="alertdialog"
        showCloseButton={false}
        className="w-full max-w-md rounded-3xl border border-destructive/20 bg-card p-6 shadow-2xl sm:p-7"
      >
        {/* Warning Icon Badge */}
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-destructive/10 text-destructive ring-8 ring-destructive/5">
          <Trash2 className="h-6 w-6" />
        </div>

        {/* Title & Description */}
        <DialogHeader className="gap-1.5 text-left">
          <DialogTitle id="voice-delete-title" className="text-xl font-black tracking-tight text-foreground sm:text-2xl">
            {t("voices.deleteDialogTitle", { name: voiceName })}
          </DialogTitle>
          <DialogDescription id="voice-delete-description" className="text-sm leading-relaxed text-muted-foreground">
            {t("voices.deleteDialogDescription")}
          </DialogDescription>
        </DialogHeader>

        {/* Extra Warning Notice */}
        <div className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 p-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <p className="text-xs font-semibold leading-relaxed text-destructive/90">
            {t("voices.deleteWarningPermanent")}
          </p>
        </div>

        {/* Action Buttons */}
        <DialogFooter className="mt-2 -mx-0 -mb-0 flex-row justify-end gap-2.5 border-t-0 bg-transparent p-0">
          <Button
            type="button"
            variant="outline"
            disabled={pending}
            onClick={onCancel}
            className="rounded-xl px-4 font-bold"
          >
            {t("common.cancel")}
          </Button>

          <Button
            type="button"
            variant="destructive"
            disabled={pending}
            onClick={onConfirm}
            className="gap-1.5 rounded-xl px-4 font-bold shadow-xs shadow-destructive/20"
          >
            {pending ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{t("voices.deletingVoice")}</span>
              </>
            ) : (
              <>
                <Trash2 className="h-3.5 w-3.5" />
                <span>{t("voices.confirmDeleteAction")}</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
