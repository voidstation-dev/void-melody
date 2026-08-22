"use client"

import Link from "next/link"
import { MoreHorizontal, Trash2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "@/hooks/use-translation"

type VoiceActionsMenuProps = { voiceId: string; onDelete: () => void; disabled?: boolean }

export function VoiceActionsMenu({ voiceId, onDelete, disabled = false }: VoiceActionsMenuProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("pointerdown", onPointerDown)
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("pointerdown", onPointerDown)
      document.removeEventListener("keydown", onKeyDown)
    }
  }, [open])

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={`${t("voices.moreActions")} ${voiceId}`}
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-10 z-20 min-w-36 rounded-xl border border-border bg-popover p-1.5 shadow-lg">
          <Link role="menuitem" href={`/?voice=${encodeURIComponent(voiceId)}`} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 text-xs font-semibold hover:bg-muted focus-visible:bg-muted focus-visible:outline-none">{t("voices.useVoice")}</Link>
          <button role="menuitem" type="button" onClick={() => { setOpen(false); onDelete() }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold text-destructive hover:bg-destructive/10 focus-visible:bg-destructive/10 focus-visible:outline-none"><Trash2 className="h-3.5 w-3.5" />{t("voices.deleteVoice")}</button>
        </div>
      )}
    </div>
  )
}
