import React, { useState } from "react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Sparkles, Check } from "lucide-react"
import type { DeliveryTag } from "../types"

interface EmotionTagProps {
  tag: DeliveryTag
  onClick: (token: string) => void
}

export function EmotionTag({ tag, onClick }: EmotionTagProps) {
  const [justClicked, setJustClicked] = useState(false)

  const handleClick = () => {
    onClick(tag.token)
    setJustClicked(true)
    setTimeout(() => setJustClicked(false), 600)
  }

  const isNative = tag.type === "native"

  const colorStyles =
    tag.colorVariant === "green"
      ? "bg-emerald-500/8 text-emerald-800 dark:text-emerald-200 border-emerald-500/25 hover:bg-emerald-500/15 hover:border-emerald-500/50 hover:shadow-xs hover:shadow-emerald-500/10"
      : tag.colorVariant === "amber"
        ? "bg-amber-500/8 text-amber-800 dark:text-amber-200 border-amber-500/25 hover:bg-amber-500/15 hover:border-amber-500/50 hover:shadow-xs hover:shadow-amber-500/10"
        : "bg-sky-500/8 text-sky-800 dark:text-sky-200 border-sky-500/25 hover:bg-sky-500/15 hover:border-sky-500/50 hover:shadow-xs hover:shadow-sky-500/10"

  return (
    <TooltipProvider delayDuration={250}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={handleClick}
            className={cn(
              "group relative inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-xs font-semibold transition-all duration-150 cursor-pointer select-none backdrop-blur-xs",
              "active:scale-95 hover:-translate-y-0.5 shadow-2xs",
              colorStyles,
              justClicked && "ring-2 ring-primary/40 scale-95",
            )}
          >
            {/* Icon / Emoji */}
            {tag.icon && (
              <span className="text-sm shrink-0 transition-transform group-hover:scale-110">
                {tag.icon}
              </span>
            )}

            {/* Label */}
            <span className="tracking-tight">{tag.label}</span>

            {/* Click Feedback or Native Sparkle */}
            {justClicked ? (
              <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
            ) : isNative ? (
              <Sparkles className="h-3 w-3 text-emerald-500/70 group-hover:text-emerald-500 shrink-0" />
            ) : null}
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-xs p-2.5 rounded-xl border border-border/80 shadow-md">
          <div className="flex items-center gap-1.5">
            {tag.icon && <span>{tag.icon}</span>}
            <p className="font-bold text-foreground">{tag.label}</p>
            <span className="font-mono text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{tag.token}</span>
          </div>
          {tag.description && <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">{tag.description}</p>}
          {isNative && (
            <p className="mt-1.5 flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
              <Sparkles className="h-3 w-3" />
              <span>Hỗ trợ trực tiếp bởi VieNeu AI</span>
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
