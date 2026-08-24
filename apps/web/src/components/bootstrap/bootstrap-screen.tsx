import React, { useState } from "react"
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  RotateCcw,
  Monitor,
  FolderCheck,
  Cpu,
  Sparkles,
  Network,
} from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { BrandMark } from "@/components/ui/brand-logo"

export type BootstrapStageId = "desktop" | "storage" | "sidecar" | "models" | "server"
export type BootstrapStageStatus = "pending" | "active" | "completed" | "error"

export type BootstrapStage = {
  id: BootstrapStageId
  title: string
  detail?: string
  status: BootstrapStageStatus
}

export type BootstrapScreenProps = {
  stages: BootstrapStage[]
  progressPercent: number
  currentStatusText: string
  logs: string
  error: string | null
  onRestart?: () => void
}

const stageIcons: Record<BootstrapStageId, React.ComponentType<{ className?: string }>> = {
  desktop: Monitor,
  storage: FolderCheck,
  sidecar: Cpu,
  models: Sparkles,
  server: Network,
}

export function BootstrapScreen({
  stages,
  progressPercent,
  currentStatusText,
  logs,
  error,
  onRestart,
}: BootstrapScreenProps) {
  const [showLogs, setShowLogs] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopyLogs = async () => {
    if (!logs) return
    try {
      await navigator.clipboard.writeText(logs)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  const isStartupTimeout = error?.includes("did not start in time")

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-background p-4 sm:p-6 select-none">
      {/* Ambient background decoration */}
      <div className="pointer-events-none fixed inset-0 flex items-center justify-center opacity-25">
        <div className="h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
      </div>

      <main className="relative z-10 w-full max-w-xl animate-in fade-in zoom-in-95 duration-300">
        <div className="overflow-hidden rounded-3xl border border-border/80 bg-card/95 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
          {/* Brand Header */}
          <div className="flex flex-col items-center text-center">
            <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-card shadow-lg ring-1 ring-border/80 p-2">
              <BrandMark className="h-full w-full" alt="Melody Logo" />
              {!error && (
                <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex h-4 w-4 rounded-full bg-primary" />
                </span>
              )}
            </div>

            <h1 className="mt-4 text-2xl font-black tracking-tight text-foreground sm:text-3xl">
              {error ? "Failed to start local API" : "Đang khởi tạo VoidMelody"}
            </h1>
            <p className="mt-1.5 text-xs text-muted-foreground sm:text-sm">
              {error
                ? "Không thể khởi chạy môi trường máy chủ cục bộ"
                : "Kiểm tra môi trường hệ thống & tải AI Voice Models"}
            </p>
          </div>

          {/* Progress Bar Section */}
          {!error && (
            <div className="mt-6 space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="truncate pr-2 text-muted-foreground">{currentStatusText}</span>
                <span className="font-mono text-primary">{Math.round(progressPercent)}%</span>
              </div>
              <Progress value={progressPercent} className="h-2.5" />
            </div>
          )}

          {/* Environment Checklist */}
          <div className="mt-6 space-y-2 rounded-2xl border border-border/60 bg-muted/20 p-3 sm:p-4">
            <h2 className="px-1 text-[11px] font-extrabold uppercase tracking-wider text-muted-foreground">
              Kiểm tra môi trường hệ thống
            </h2>

            <div className="divide-y divide-border/40">
              {stages.map((stage) => {
                const Icon = stageIcons[stage.id] || Monitor
                const isCurrentActive = stage.status === "active"
                const isCompleted = stage.status === "completed"
                const isFailed = stage.status === "error"

                return (
                  <div
                    key={stage.id}
                    className={`flex items-center justify-between gap-3 py-2.5 px-2 transition-colors rounded-xl ${
                      isCurrentActive ? "bg-primary/5" : ""
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-colors ${
                          isCompleted
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                            : isCurrentActive
                              ? "bg-primary/10 text-primary"
                              : isFailed
                                ? "bg-destructive/10 text-destructive"
                                : "bg-muted text-muted-foreground/60"
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>

                      <div className="min-w-0">
                        <p
                          className={`text-xs font-bold tracking-tight truncate ${
                            isCompleted || isCurrentActive ? "text-foreground" : "text-muted-foreground"
                          }`}
                        >
                          {stage.title}
                        </p>
                        {stage.detail && (
                          <p className="truncate text-[11px] text-muted-foreground">
                            {stage.detail}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="shrink-0">
                      {isCompleted && (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 animate-in fade-in zoom-in-75" />
                      )}
                      {isCurrentActive && (
                        <Loader2 className="h-4 w-4 text-primary animate-spin" />
                      )}
                      {isFailed && (
                        <AlertCircle className="h-4 w-4 text-destructive animate-in fade-in" />
                      )}
                      {stage.status === "pending" && (
                        <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/30" />
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Error Diagnostics & Action */}
          {error && (
            <div className="mt-5 space-y-4 rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-left animate-in fade-in">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-destructive">Lỗi khởi động API Sidecar:</p>
                  <p className="mt-1 font-mono text-[11px] leading-relaxed text-destructive/90 break-words">
                    {error}
                  </p>
                </div>
              </div>

              {isStartupTimeout && (
                <div className="space-y-2 text-xs text-muted-foreground border-t border-destructive/20 pt-3">
                  <p className="font-semibold text-foreground">Hướng dẫn xử lý / Troubleshooting:</p>
                  <div className="space-y-1 text-xs">
                    <p className="font-semibold text-foreground">macOS:</p>
                    <p className="text-[11px]">macOS may be blocking the bundled API binary. Run:</p>
                    <pre className="rounded bg-muted p-2 text-xs font-mono text-foreground select-all">
                      xattr -cr /Applications/VoidMelody.app
                    </pre>
                  </div>
                  <div className="space-y-1 text-xs pt-1">
                    <p className="font-semibold text-foreground">Windows / Linux:</p>
                    <p className="text-[11px]">
                      Ensure antivirus is not locking temp files and close any background instances, then click Restart API.
                    </p>
                  </div>
                </div>
              )}

              {onRestart && (
                <Button
                  onClick={onRestart}
                  variant="default"
                  className="w-full gap-2 rounded-xl font-bold"
                >
                  <RotateCcw className="h-4 w-4" />
                  Restart API / Thử lại
                </Button>
              )}
            </div>
          )}

          {/* Live Log Console Toggle */}
          {logs && (
            <div className="mt-4 border-t border-border/60 pt-3">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setShowLogs((prev) => !prev)}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showLogs ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  <span>{showLogs ? "Ẩn log tiến trình" : "Xem log chi tiết (Console)"}</span>
                </button>

                {showLogs && (
                  <button
                    type="button"
                    onClick={handleCopyLogs}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground"
                  >
                    {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                    <span>{copied ? "Đã chép" : "Sao chép"}</span>
                  </button>
                )}
              </div>

              {showLogs && (
                <div className="mt-2.5 max-h-48 overflow-y-auto rounded-xl border border-border/80 bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300 shadow-inner">
                  <pre className="whitespace-pre-wrap leading-relaxed select-text">{logs}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
