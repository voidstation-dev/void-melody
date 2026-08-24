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
import { useTranslation } from "@/hooks/use-translation"

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
  const { t } = useTranslation()
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
    <div className="fixed inset-0 h-screen w-screen overflow-y-auto bg-background p-4 sm:p-6 select-none flex flex-col items-center justify-start sm:justify-center">
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
              {error ? t("bootstrap.titleFailed") : t("bootstrap.titleInitializing")}
            </h1>
            <p className="mt-1.5 text-xs text-muted-foreground sm:text-sm">
              {error ? t("bootstrap.subtitleFailed") : t("bootstrap.subtitleInitializing")}
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
              {t("bootstrap.checklistHeading")}
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
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                            : isCurrentActive
                              ? "bg-primary/10 text-primary border border-primary/30 ring-2 ring-primary/20"
                              : isFailed
                                ? "bg-destructive/10 text-destructive border border-destructive/30"
                                : "bg-muted text-muted-foreground border border-border/40"
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-xs font-bold leading-none truncate ${
                            isCompleted || isCurrentActive ? "text-foreground" : "text-muted-foreground"
                          }`}
                        >
                          {stage.title}
                        </p>
                        {stage.detail && (
                          <p className="mt-1 text-[11px] text-muted-foreground/80 leading-none truncate">
                            {stage.detail}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center">
                      {isCompleted && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                      {isCurrentActive && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                      {isFailed && <AlertCircle className="h-4 w-4 text-destructive" />}
                      {!isCompleted && !isCurrentActive && !isFailed && (
                        <div className="h-2 w-2 rounded-full bg-border mr-1" />
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
                  <p className="text-xs font-bold text-destructive">{t("bootstrap.errorHeading")}</p>
                  <p className="mt-1 font-mono text-[11px] leading-relaxed text-destructive/90 break-words">
                    {error}
                  </p>
                </div>
              </div>

              {isStartupTimeout && (
                <div className="space-y-2 text-xs text-muted-foreground border-t border-destructive/20 pt-3">
                  <p className="font-semibold text-foreground">{t("bootstrap.troubleshootingHeading")}</p>
                  <div className="space-y-1 text-xs">
                    <p className="font-semibold text-foreground">{t("bootstrap.macosGuideTitle")}</p>
                    <p className="text-[11px]">{t("bootstrap.macosGuideText")}</p>
                    <pre className="rounded bg-muted p-2 text-xs font-mono text-foreground select-all">
                      xattr -cr /Applications/VoidMelody.app
                    </pre>
                  </div>
                  <div className="space-y-1 text-xs pt-1">
                    <p className="font-semibold text-foreground">{t("bootstrap.windowsGuideTitle")}</p>
                    <p className="text-[11px]">
                      {t("bootstrap.windowsGuideText")}
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
                  {t("bootstrap.restartBtn")}
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
                  <span>{showLogs ? t("bootstrap.hideLogs") : t("bootstrap.viewLogs")}</span>
                </button>

                {showLogs && (
                  <button
                    type="button"
                    onClick={handleCopyLogs}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground"
                  >
                    {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                    <span>{copied ? t("bootstrap.copiedLogs") : t("bootstrap.copyLogs")}</span>
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
