"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { AlertTriangle, Clock3, LockKeyhole } from "lucide-react"
import { apiFetch, onTrialBlocked } from "@/lib/api-client"
import type { TrialStatus } from "@/types/trial"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

const DEFAULT_STATUS: TrialStatus = {
  status: "ACTIVE",
  can_synthesize: true,
  first_run_at: null,
  expires_at: null,
  remaining_seconds: -1,
  warning_level: "NONE",
  override: "browser-default",
}

type TrialContextValue = {
  status: TrialStatus
  isLoading: boolean
  refresh: () => Promise<void>
  openExpiredDialog: () => void
}

const TrialContext = createContext<TrialContextValue | null>(null)

export function useTrialStatus(): TrialContextValue {
  return useContext(TrialContext) ?? {
    status: DEFAULT_STATUS,
    isLoading: false,
    refresh: async () => undefined,
    openExpiredDialog: () => undefined,
  }
}

function remainingLabel(seconds: number) {
  const days = Math.floor(seconds / 86400)
  if (days > 0) return `${days} ngày`
  const hours = Math.max(1, Math.ceil(seconds / 3600))
  return `${hours} giờ`
}

function TrialWarningBanner({ onDetails }: { onDetails: () => void }) {
  const { status } = useTrialStatus()
  if (status.override || (status.status === "ACTIVE" && status.warning_level === "NONE")) return null
  const expired = status.status !== "EXPIRING"
  return (
    <div className={`fixed inset-x-3 top-3 z-40 mx-auto flex max-w-3xl items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm shadow-lg backdrop-blur ${expired ? "border-red-200 bg-red-50/95 text-red-900" : "border-amber-200 bg-amber-50/95 text-amber-950"}`} role="status">
      <div className="flex min-w-0 items-center gap-2">
        {expired ? <LockKeyhole className="h-4 w-4 shrink-0" /> : <Clock3 className="h-4 w-4 shrink-0" />}
        <span className="truncate font-semibold">
          {expired ? "Thời gian dùng thử đã kết thúc — tạo audio mới đang bị khóa." : `Thời gian dùng thử còn ${remainingLabel(status.remaining_seconds)}.`}
        </span>
      </div>
      <Button type="button" variant="ghost" size="sm" onClick={onDetails} className="shrink-0">Chi tiết</Button>
    </div>
  )
}

function TrialExpiredDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-600" />Thời gian dùng thử đã kết thúc</DialogTitle>
          <DialogDescription>
            Bạn vẫn có thể xem, phát và tải các audio đã tạo trước đó. Chức năng tạo audio mới hiện bị khóa.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter showCloseButton>
          <Button type="button" onClick={() => onOpenChange(false)}>Đã hiểu</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function TrialProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<TrialStatus>(DEFAULT_STATUS)
  const [isLoading, setIsLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const next = await apiFetch<TrialStatus>("/api/v1/trial/status")
      setStatus(next)
    } catch {
      // The API may still be booting; keep the last known UX state and retry
      // on focus/interval rather than blocking navigation.
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // Initial status sync is intentionally kicked off after the provider mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
    const unsubscribe = onTrialBlocked(() => {
      setDialogOpen(true)
      void refresh()
    })
    const onFocus = () => void refresh()
    window.addEventListener("focus", onFocus)
    const timer = window.setInterval(() => void refresh(), 60_000)
    return () => {
      unsubscribe()
      window.removeEventListener("focus", onFocus)
      window.clearInterval(timer)
    }
  }, [refresh])

  const value = useMemo(() => ({ status, isLoading, refresh, openExpiredDialog: () => setDialogOpen(true) }), [isLoading, refresh, status])
  return (
    <TrialContext.Provider value={value}>
      {children}
      <TrialWarningBanner onDetails={() => setDialogOpen(true)} />
      <TrialExpiredDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </TrialContext.Provider>
  )
}
