import React from "react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import type { DeliveryTag } from "../types"

interface EmotionTagProps {
  tag: DeliveryTag
  onClick: (token: string) => void
}

export function EmotionTag({ tag, onClick }: EmotionTagProps) {
  const colorStyles =
    tag.colorVariant === "green"
      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20 active:scale-95"
      : tag.colorVariant === "amber"
        ? "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30 hover:bg-amber-500/20 active:scale-95"
        : "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30 hover:bg-sky-500/20 active:scale-95"

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => onClick(tag.token)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none",
              colorStyles
            )}
          >
            <span>{tag.label}</span>
            <span className="font-mono text-[10px] opacity-70">{tag.token}</span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-xs">
          <p className="font-bold">{tag.label}</p>
          {tag.description && <p className="mt-0.5 text-[11px] text-muted-foreground">{tag.description}</p>}
          {tag.type === "native" && (
            <p className="mt-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
              ⚡ Hỗ trợ trực tiếp bởi VieNeu AI
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
