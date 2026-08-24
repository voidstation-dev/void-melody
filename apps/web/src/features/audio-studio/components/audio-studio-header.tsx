import { Sparkles, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface AudioStudioHeaderProps {
  lastSavedAt: number | null
  cueCount?: number
}

export function AudioStudioHeader({ lastSavedAt, cueCount = 0 }: AudioStudioHeaderProps) {
  const formattedSavedTime = lastSavedAt
    ? new Date(lastSavedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : null

  const isEmotional = cueCount > 0

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between shrink-0">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-xl sm:text-2xl font-black tracking-tight text-foreground">Tạo audio mới</h1>
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-bold text-primary border border-primary/20">
            <Sparkles className="h-3 w-3" />
            Studio
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold border transition-colors",
              isEmotional
                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                : "bg-muted text-muted-foreground border-border",
            )}
          >
            {isEmotional ? `Mode Cảm xúc (${cueCount} thẻ)` : "Mode Tiêu chuẩn"}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Soạn nội dung, chèn cảm xúc ngữ điệu, chọn giọng đọc và tạo audio chất lượng cao.
        </p>
      </div>

      {formattedSavedTime && (
        <div className="flex items-center gap-1.5 self-start sm:self-auto rounded-full bg-muted/60 px-3 py-1 text-[11px] font-medium text-muted-foreground border border-border/40">
          <CheckCircle2 className="h-3 w-3 text-emerald-500" />
          <span>Đã lưu tự động lúc {formattedSavedTime}</span>
        </div>
      )}
    </div>
  )
}
