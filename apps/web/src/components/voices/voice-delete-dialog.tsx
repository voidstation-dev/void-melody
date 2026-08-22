"use client"

import { useEffect, useRef } from "react"
import { useTranslation } from "@/hooks/use-translation"

type VoiceDeleteDialogProps = { open: boolean; voiceName: string; pending?: boolean; onCancel: () => void; onConfirm: () => void }

export function VoiceDeleteDialog({ open, voiceName, pending = false, onCancel, onConfirm }: VoiceDeleteDialogProps) {
  const { t } = useTranslation()
  const cancelRef = useRef<HTMLButtonElement | null>(null)
  const dialogRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !pending) onCancel()
      if (event.key === "Tab") {
        const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea, [tabindex]:not([tabindex=\"-1\"])") ?? []).filter((element) => !element.hasAttribute("disabled"))
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [open, onCancel, pending])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4" role="presentation">
      <div ref={dialogRef} role="alertdialog" aria-modal="true" aria-labelledby="voice-delete-title" aria-describedby="voice-delete-description" className="w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <h2 id="voice-delete-title" className="text-lg font-black tracking-tight">{t("voices.deleteDialogTitle", { name: voiceName })}</h2>
        <p id="voice-delete-description" className="mt-2 text-sm leading-6 text-muted-foreground">{t("voices.deleteDialogDescription")}</p>
        <div className="mt-6 flex justify-end gap-2">
          <button ref={cancelRef} type="button" disabled={pending} onClick={onCancel} className="min-h-9 rounded-xl border border-border px-3.5 text-xs font-bold transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50">{t("common.cancel")}</button>
          <button type="button" disabled={pending} onClick={onConfirm} className="min-h-9 rounded-xl bg-destructive px-3.5 text-xs font-bold text-destructive-foreground transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive disabled:cursor-wait disabled:opacity-50">{pending ? t("voices.deletingVoice") : t("voices.confirmDeleteAction")}</button>
        </div>
      </div>
    </div>
  )
}
