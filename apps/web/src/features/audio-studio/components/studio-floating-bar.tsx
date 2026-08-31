import { useState } from "react"
import {
  Sparkles,
  Loader2,
  Mic,
  Zap,
  Volume2,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  AlignLeft,
  Smile,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTranslation } from "@/hooks/use-translation"
import { cn } from "@/lib/utils"
import type { PreflightReport, VoiceItem } from "../types"

interface StudioFloatingBarProps {
  selectedVoice: VoiceItem | null
  speed: number
  outputFormat: "mp3" | "wav"
  report: PreflightReport
  isSubmitting: boolean
  onGenerate: () => void
}

export function StudioFloatingBar({
  selectedVoice,
  speed,
  outputFormat,
  report,
  isSubmitting,
  onGenerate,
}: StudioFloatingBarProps) {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const isMac = typeof window !== "undefined" && /Mac|iPod|iPhone|iPad/.test(navigator.userAgent)
  const { stats, checks, canGenerate } = report
  const isEmotional = stats.emotionCount > 0 || stats.nativeCueCount > 0

  return (
    <aside
      aria-label="Studio Action Bar"
      className="sticky bottom-3 sm:bottom-4 z-40 w-full animate-in fade-in slide-in-from-bottom-3 duration-300 pointer-events-auto"
    >
      <div className="rounded-2xl sm:rounded-3xl border border-border/80 bg-card/95 dark:bg-card/95 p-2.5 sm:p-3 shadow-2xl backdrop-blur-xl ring-1 ring-black/5 dark:ring-white/10 transition-all duration-300 space-y-0">
        {/* Main Dock Summary Bar (Always Single-Row, Clickable to Toggle) */}
        <div
          onClick={() => setIsExpanded((prev) => !prev)}
          className="flex items-center justify-between gap-2.5 sm:gap-3 cursor-pointer select-none group/bar"
          title={isExpanded ? "Bấm để thu gọn chi tiết" : "Bấm để xem chi tiết kiểm tra kết xuất"}
        >
          {/* Left Section: Selected Voice, Mode & Specs */}
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1 flex-wrap">
            {/* Voice Pill */}
            <div className="flex items-center gap-2 rounded-xl bg-muted/60 px-2.5 sm:px-3 py-1.5 sm:py-2 border border-border/50 max-w-[170px] sm:max-w-[220px] shrink-0">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Mic className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1 truncate">
                <p className="truncate text-xs font-bold text-foreground">
                  {selectedVoice?.displayName || t("audioStudio.voiceNotSelected", "Chưa chọn giọng")}
                </p>
                <p className="truncate text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                  {selectedVoice?.providerId === "vieneu"
                    ? "VieNeu AI"
                    : selectedVoice?.providerId === "omnivoice"
                      ? "OmniVoice"
                      : "CapCut Cloud"}
                </p>
              </div>
            </div>

            {/* Quick Specs Pill */}
            <div className="hidden sm:flex items-center gap-2 rounded-xl bg-muted/40 px-2.5 sm:px-3 py-1.5 sm:py-2 border border-border/30 text-xs font-medium text-muted-foreground shrink-0">
              <span className="font-mono font-bold text-foreground">⚡ {speed.toFixed(2)}x</span>
              <span>·</span>
              <span className="font-mono font-bold uppercase text-foreground">{outputFormat}</span>
              <span>·</span>
              {isEmotional ? (
                <span className="flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                  <Sparkles className="h-3 w-3" />
                  <span>{stats.nativeCueCount + stats.emotionCount} sắc thái</span>
                </span>
              ) : (
                <span className="flex items-center gap-1 font-medium text-muted-foreground">
                  <Volume2 className="h-3 w-3" />
                  <span>Tiêu chuẩn</span>
                </span>
              )}
            </div>

            {/* Text Stats */}
            <div className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground pl-1 font-medium truncate">
              <span>
                {stats.segmentCount.toLocaleString()} {t("audioStudio.statsSegments")}
              </span>
              <span>({stats.characterCount.toLocaleString()} ký tự)</span>
            </div>
          </div>

          {/* Right Section: Preflight Status Toggle & Primary CTA Button */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Preflight Status Toggle Button */}
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-xl px-2.5 sm:px-3 py-1.5 sm:py-2 text-[11px] font-bold border transition-all shadow-2xs cursor-pointer",
                canGenerate
                  ? "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/25"
                  : "bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/25",
                isExpanded && "ring-2 ring-primary/20"
              )}
            >
              <span
                className={cn(
                  "h-2 w-2 rounded-full shrink-0",
                  canGenerate ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                )}
              />
              <span className="hidden sm:inline">
                {canGenerate ? t("audioStudio.ready") : t("audioStudio.notReady")}
              </span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 opacity-70 transition-transform duration-300",
                  isExpanded && "rotate-180 text-primary"
                )}
              />
            </div>

            {/* Primary Action Button: Generate Audio */}
            <Button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onGenerate()
              }}
              disabled={!canGenerate || isSubmitting}
              className={cn(
                "h-9 sm:h-10 rounded-xl sm:rounded-2xl px-3.5 sm:px-5 text-xs sm:text-sm font-bold shadow-md transition-all cursor-pointer gap-2 shrink-0",
                canGenerate && !isSubmitting
                  ? "bg-primary hover:bg-primary/90 text-primary-foreground shadow-primary/25 hover:scale-[1.02] active:scale-[0.98]"
                  : "opacity-50 cursor-not-allowed"
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>{t("audioStudio.generatingBtn")}</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 fill-current" />
                  <span>{t("audioStudio.generateBtn")}</span>
                  <kbd className="hidden lg:inline-flex items-center rounded-md bg-primary-foreground/20 px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wide">
                    {isMac ? "⌘ + ↵" : "Ctrl + ↵"}
                  </kbd>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Expandable Area: Full Preflight Inspection Details */}
        <div
          className={cn(
            "grid transition-all duration-300 ease-out",
            isExpanded
              ? "grid-rows-[1fr] opacity-100 mt-3 pt-3 border-t border-border/60"
              : "grid-rows-[0fr] opacity-0 mt-0 pt-0 border-t-0 pointer-events-none"
          )}
        >
          <div className="overflow-hidden space-y-3 pt-1">
            {/* Header */}
            <div className="flex items-center justify-between pb-2 border-b border-border/60">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <ShieldCheck className="h-3.5 w-3.5" />
                </div>
                <h4 className="text-xs font-black uppercase tracking-wider text-foreground">
                  {t("audioStudio.preflightTitle")}
                </h4>
              </div>
              <span
                className={cn(
                  "text-[10px] font-bold px-2 py-0.5 rounded-full border",
                  canGenerate
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                    : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
                )}
              >
                {canGenerate ? t("audioStudio.ready") : t("audioStudio.notReady")}
              </span>
            </div>

            {/* Mode Banner */}
            <div
              className={cn(
                "flex items-start gap-2.5 rounded-xl p-3 border text-xs leading-relaxed",
                isEmotional
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-950 dark:text-amber-100"
                  : "bg-muted/40 border-border/60 text-foreground"
              )}
            >
              <div
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg mt-0.5",
                  isEmotional
                    ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                    : "bg-primary/10 text-primary"
                )}
              >
                {isEmotional ? <Sparkles className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-bold">
                  {isEmotional
                    ? t("audioStudio.modeExpressiveTitle")
                    : t("audioStudio.modeStandardTitle")}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {isEmotional
                    ? t("audioStudio.modeExpressiveDesc", {
                        cues: stats.nativeCueCount,
                        emotions: stats.emotionCount,
                      })
                    : t("audioStudio.modeStandardDesc")}
                </p>
              </div>
            </div>

            {/* Mini Stats Grid */}
            <div className="grid grid-cols-3 divide-x divide-border/60 rounded-xl bg-muted/30 border border-border/60 p-2 text-center">
              <div className="flex flex-col items-center justify-center px-1">
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground mb-0.5 font-medium">
                  <AlignLeft className="h-3 w-3" />
                  <span>{t("audioStudio.statsSegments")}</span>
                </div>
                <span className="text-xs font-black text-foreground">{stats.segmentCount}</span>
              </div>

              <div className="flex flex-col items-center justify-center px-1">
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground mb-0.5 font-medium">
                  <Zap className={cn("h-3 w-3", stats.nativeCueCount > 0 && "text-emerald-500")} />
                  <span>Native Cues</span>
                </div>
                <span
                  className={cn(
                    "text-xs font-black",
                    stats.nativeCueCount > 0
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-foreground"
                  )}
                >
                  {stats.nativeCueCount}
                </span>
              </div>

              <div className="flex flex-col items-center justify-center px-1">
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground mb-0.5 font-medium">
                  <Smile className={cn("h-3 w-3", stats.emotionCount > 0 && "text-amber-500")} />
                  <span>Cảm xúc</span>
                </div>
                <span
                  className={cn(
                    "text-xs font-black",
                    stats.emotionCount > 0
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-foreground"
                  )}
                >
                  {stats.emotionCount}
                </span>
              </div>
            </div>

            {/* Detailed Checklist */}
            <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
              {checks.map((check) => {
                const Icon =
                  check.severity === "success"
                    ? CheckCircle2
                    : check.severity === "warning"
                      ? AlertTriangle
                      : check.severity === "error"
                        ? AlertCircle
                        : Info

                const iconColor =
                  check.severity === "success"
                    ? "text-emerald-500"
                    : check.severity === "warning"
                      ? "text-amber-500"
                      : check.severity === "error"
                        ? "text-rose-500"
                        : "text-primary"

                return (
                  <div
                    key={check.id}
                    className="flex items-start gap-2 rounded-lg p-2 bg-muted/30 border border-border/40 text-[11px]"
                  >
                    <Icon className={cn("h-3.5 w-3.5 shrink-0 mt-0.5", iconColor)} />
                    <div className="min-w-0 flex-1 leading-snug">
                      <p className="font-semibold text-foreground/90">{check.message}</p>
                      {check.detail && (
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {check.detail}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Bottom Row: Collapse Button */}
            <div className="flex items-center justify-end pt-1">
              <button
                type="button"
                onClick={() => setIsExpanded(false)}
                className="rounded-xl border border-border bg-background px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
              >
                Thu gọn ▲
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
