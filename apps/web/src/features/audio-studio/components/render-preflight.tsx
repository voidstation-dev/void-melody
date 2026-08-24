import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  Sparkles,
  ShieldCheck,
  Volume2,
  AlignLeft,
  Smile,
  Zap,
} from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { PreflightReport } from "../types"
import { cn } from "@/lib/utils"

interface RenderPreflightProps {
  report: PreflightReport
}

export function RenderPreflight({ report }: RenderPreflightProps) {
  const { stats, checks, canGenerate } = report
  const isEmotional = stats.emotionCount > 0 || stats.nativeCueCount > 0

  return (
    <Card className="border border-border/80 bg-card text-card-foreground shadow-sm rounded-2xl overflow-hidden transition-all duration-200">
      {/* Header */}
      <CardHeader className="p-4 pb-3 border-b border-border/60 bg-muted/20">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-foreground">
                Kiểm tra kết xuất
              </h3>
              <p className="text-[10px] text-muted-foreground">Preflight Verification</p>
            </div>
          </div>

          {/* Status Badge */}
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold border transition-colors",
              canGenerate
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
            )}
          >
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                canGenerate ? "bg-emerald-500 animate-pulse" : "bg-rose-500",
              )}
            />
            <span>{canGenerate ? "Sẵn sàng" : "Chưa hoàn tất"}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 space-y-3.5">
        {/* Pipeline Mode Banner */}
        <div
          className={cn(
            "flex items-start gap-3.5 rounded-xl p-4 sm:p-4.5 border transition-colors",
            isEmotional
              ? "bg-amber-500/5 border-amber-500/30 text-amber-950 dark:text-amber-100"
              : "bg-muted/40 border-border/60 text-foreground",
          )}
        >
          <div
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl mt-0.5",
              isEmotional
                ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                : "bg-primary/10 text-primary",
            )}
          >
            {isEmotional ? <Sparkles className="h-4.5 w-4.5" /> : <Volume2 className="h-4.5 w-4.5" />}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs sm:text-[13px] font-bold">
                {isEmotional ? "Chế độ: Đa ngữ điệu & Cảm xúc" : "Chế độ: Đọc tiêu chuẩn"}
              </span>
              <span
                className={cn(
                  "text-[9px] sm:text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md font-mono",
                  isEmotional
                    ? "bg-amber-500/20 text-amber-700 dark:text-amber-300"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {isEmotional ? "Expressive" : "Standard"}
              </span>
            </div>
            <p className="text-[11px] sm:text-xs text-muted-foreground mt-1 leading-relaxed">
              {isEmotional
                ? `Tự động phân đoạn và áp dụng ${stats.nativeCueCount} Native cues, ${stats.emotionCount} sắc thái cảm xúc`
                : "Tổng hợp văn bản liền mạch theo cấu hình giọng và tốc độ đã chọn"}
            </p>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-3 divide-x divide-border/60 rounded-xl bg-muted/30 border border-border/60 p-2 text-center">
          <div className="flex flex-col items-center justify-center px-1">
            <div className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground mb-0.5">
              <AlignLeft className="h-3 w-3" />
              <span>Đoạn văn</span>
            </div>
            <span className="text-sm font-extrabold text-foreground">{stats.segmentCount}</span>
          </div>

          <div className="flex flex-col items-center justify-center px-1">
            <div className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground mb-0.5">
              <Zap className={cn("h-3 w-3", stats.nativeCueCount > 0 && "text-emerald-500")} />
              <span>Native cues</span>
            </div>
            <span
              className={cn(
                "text-sm font-extrabold",
                stats.nativeCueCount > 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-foreground",
              )}
            >
              {stats.nativeCueCount}
            </span>
          </div>

          <div className="flex flex-col items-center justify-center px-1">
            <div className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground mb-0.5">
              <Smile className={cn("h-3 w-3", stats.emotionCount > 0 && "text-amber-500")} />
              <span>Cảm xúc</span>
            </div>
            <span
              className={cn(
                "text-sm font-extrabold",
                stats.emotionCount > 0 ? "text-amber-600 dark:text-amber-400" : "text-foreground",
              )}
            >
              {stats.emotionCount}
            </span>
          </div>
        </div>

        {/* Detailed Status Checklist */}
        <div className="space-y-1.5 pt-1">
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
                className="flex items-start gap-2.5 rounded-lg p-2 bg-background/50 border border-border/40 text-xs transition-colors hover:bg-muted/30"
              >
                <Icon className={cn("h-3.5 w-3.5 shrink-0 mt-0.5", iconColor)} />
                <div className="min-w-0 flex-1 leading-tight">
                  <p className="font-semibold text-foreground/90">{check.message}</p>
                  {check.detail && (
                    <p className="text-[11px] text-muted-foreground mt-0.5">{check.detail}</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
