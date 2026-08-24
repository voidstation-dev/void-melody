import { CheckCircle2, AlertTriangle, AlertCircle, Info, FileText, Sparkles, Layers } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PreflightReport } from "../types"
import { cn } from "@/lib/utils"

interface RenderPreflightProps {
  report: PreflightReport
}

export function RenderPreflight({ report }: RenderPreflightProps) {
  const { stats, checks } = report

  return (
    <Card className="border-border bg-slate-950 text-slate-100 shadow-md">
      <CardHeader className="pb-3 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/20 text-primary">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <CardTitle className="text-xs font-black uppercase tracking-wider text-slate-200">
              Kiểm tra kết xuất (Preflight)
            </CardTitle>
          </div>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide",
              report.canGenerate ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400",
            )}
          >
            {report.canGenerate ? "Sẵn sàng" : "Chưa hoàn tất"}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Mode Indicator Banner */}
        <div
          className={cn(
            "flex items-center gap-2.5 rounded-xl px-3 py-2 border text-xs font-semibold",
            stats.emotionCount > 0 || stats.nativeCueCount > 0
              ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
              : "bg-slate-900 border-slate-800 text-slate-300",
          )}
        >
          <div
            className={cn(
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-lg",
              stats.emotionCount > 0 || stats.nativeCueCount > 0
                ? "bg-amber-500/20 text-amber-400"
                : "bg-slate-800 text-slate-400",
            )}
          >
            {stats.emotionCount > 0 || stats.nativeCueCount > 0 ? (
              <Sparkles className="h-3.5 w-3.5" />
            ) : (
              <FileText className="h-3.5 w-3.5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold">
                {stats.emotionCount > 0 || stats.nativeCueCount > 0
                  ? "Chế độ: Đa ngữ điệu & Cảm xúc"
                  : "Chế độ: Đọc chuẩn (Standard TTS)"}
              </span>
              <span className="text-[9px] uppercase tracking-wider opacity-75 font-mono">
                {stats.emotionCount > 0 || stats.nativeCueCount > 0 ? "Expressive" : "Direct"}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-normal truncate">
              {stats.emotionCount > 0 || stats.nativeCueCount > 0
                ? `Đang kích hoạt ${stats.emotionCount + stats.nativeCueCount} điểm nhấn biểu cảm`
                : "Đọc toàn bộ văn bản liền mạch theo cấu hình giọng"}
            </p>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-3 gap-2 rounded-xl bg-slate-900/80 p-2.5 border border-slate-800/80">
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-slate-400">Đoạn văn</span>
            <span className="text-base font-black text-slate-100">{stats.segmentCount}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-slate-400">Native cues</span>
            <span className="text-base font-black text-emerald-400">{stats.nativeCueCount}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-slate-400">Cảm xúc</span>
            <span className="text-base font-black text-amber-400">{stats.emotionCount}</span>
          </div>
        </div>

        {/* Status Checklist */}
        <div className="space-y-2 text-xs">
          {checks.map((check) => {
            const Icon =
              check.severity === "success"
                ? CheckCircle2
                : check.severity === "warning"
                  ? AlertTriangle
                  : check.severity === "error"
                    ? AlertCircle
                    : Info

            const textColor =
              check.severity === "success"
                ? "text-emerald-400"
                : check.severity === "warning"
                  ? "text-amber-400"
                  : check.severity === "error"
                    ? "text-rose-400"
                    : "text-sky-400"

            return (
              <div key={check.id} className="flex items-start gap-2 text-[11px] leading-relaxed">
                <Icon className={cn("h-3.5 w-3.5 shrink-0 mt-0.5", textColor)} />
                <div className="min-w-0">
                  <p className={cn("font-semibold", textColor)}>{check.message}</p>
                  {check.detail && (
                    <p className="text-[10px] text-slate-400 mt-0.5">{check.detail}</p>
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
