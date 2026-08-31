import React, { useState, useMemo } from "react"
import {
  Sparkles,
  Search,
  Plus,
  Zap,
  Smile,
  Volume2,
  Check,
} from "lucide-react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  NATIVE_CUES,
  EMOTION_TAGS,
  ADVANCED_DELIVERY_TAGS,
  ALL_TAGS,
} from "../lib/delivery-tags"
import type { DeliveryTag } from "../types"
import { useTranslation } from "@/hooks/use-translation"
import { cn } from "@/lib/utils"

interface InlineTagRibbonProps {
  onInsertTag: (tag: DeliveryTag) => void
  disabled?: boolean
}

// Quick access top tags for the inline ribbon
const QUICK_RIBBON_TAGS: DeliveryTag[] = [
  NATIVE_CUES[0], // 😄 Cười
  NATIVE_CUES[1], // 😮‍💨 Thở dài
  EMOTION_TAGS[0], // 🧘 Bình tĩnh
  EMOTION_TAGS[1], // ✨ Vui vẻ
  EMOTION_TAGS[2], // 💧 Buồn bã
  EMOTION_TAGS[4], // 🔥 Tức giận
  ADVANCED_DELIVERY_TAGS[0], // 🐢 Chậm
  ADVANCED_DELIVERY_TAGS[1], // 🐇 Nhanh
  ADVANCED_DELIVERY_TAGS[2], // ⏸️ Ngắt
]

export function InlineTagRibbon({ onInsertTag, disabled }: InlineTagRibbonProps) {
  const { t } = useTranslation()
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<"all" | "native" | "emotion" | "delivery">("all")
  const [recentlyInsertedId, setRecentlyInsertedId] = useState<string | null>(null)

  const handleSelectTag = (tag: DeliveryTag) => {
    if (disabled) return
    onInsertTag(tag)
    setRecentlyInsertedId(tag.id)
    setTimeout(() => setRecentlyInsertedId(null), 700)
  }

  const filteredPaletteTags = useMemo(() => {
    return ALL_TAGS.filter((tag) => {
      const matchesCategory =
        selectedCategory === "all" || tag.type === selectedCategory
      const query = searchQuery.trim().toLowerCase()
      const matchesSearch =
        !query ||
        tag.label.toLowerCase().includes(query) ||
        tag.token.toLowerCase().includes(query) ||
        (tag.description && tag.description.toLowerCase().includes(query))
      return matchesCategory && matchesSearch
    })
  }, [searchQuery, selectedCategory])

  return (
    <div className="flex items-center justify-between gap-2 border-t border-border/50 bg-muted/20 px-3 py-2 text-xs">
      {/* Left: Quick tag pills with horizontal scroll */}
      <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar-hidden py-0.5 min-w-0 flex-1">
        <span className="text-[11px] font-bold text-muted-foreground shrink-0 mr-1 hidden sm:inline-flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-primary" />
          <span>Chèn nhanh:</span>
        </span>

        {QUICK_RIBBON_TAGS.map((tag) => {
          const isJustClicked = recentlyInsertedId === tag.id
          const isNative = tag.type === "native"

          return (
            <button
              key={tag.id}
              type="button"
              disabled={disabled}
              onClick={() => handleSelectTag(tag)}
              title={`${tag.token} - ${tag.description || tag.label}`}
              className={cn(
                "group relative inline-flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all duration-150 cursor-pointer select-none active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed",
                isJustClicked
                  ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/40"
                  : isNative
                    ? "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/25"
                    : tag.type === "emotion"
                      ? "bg-amber-500/10 hover:bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/25"
                      : "bg-background/80 hover:bg-muted text-foreground border border-border/60 hover:border-primary/40"
              )}
            >
              <span className="text-xs leading-none">{tag.icon}</span>
              <span>{tag.label}</span>
              {isJustClicked && (
                <Check className="h-3 w-3 text-emerald-600 dark:text-emerald-400 animate-in zoom-in-50" />
              )}
            </button>
          )
        })}

        {/* All Tags Popover Button */}
        <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              disabled={disabled}
              className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 px-2.5 py-1 text-xs font-bold transition-colors cursor-pointer select-none active:scale-95"
            >
              <Plus className="h-3 w-3" />
              <span>Tất cả thẻ (19)</span>
            </button>
          </PopoverTrigger>

          <PopoverContent
            align="start"
            sideOffset={8}
            className="w-80 sm:w-[380px] rounded-2xl border-border/80 bg-card p-3.5 text-card-foreground shadow-2xl backdrop-blur-xl"
          >
            {/* Popover Header & Search */}
            <div className="space-y-2.5 pb-2.5 border-b border-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-bold text-xs">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  <span>Kho biểu cảm & Ngữ điệu</span>
                </div>
                <span className="text-[10px] font-mono font-semibold text-muted-foreground bg-muted px-2 py-0.5 rounded-md">
                  19 tags
                </span>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Tìm kiếm thẻ cảm xúc, ngữ điệu..."
                  className="h-8 w-full rounded-xl border border-border/70 bg-muted/40 pl-8 pr-3 text-xs outline-none focus:border-primary focus:bg-background transition-colors"
                />
              </div>

              {/* Category Filter Tabs */}
              <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar-hidden text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => setSelectedCategory("all")}
                  className={cn(
                    "rounded-lg px-2.5 py-1 transition-colors cursor-pointer",
                    selectedCategory === "all"
                      ? "bg-primary text-primary-foreground font-bold shadow-xs"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  Tất cả
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCategory("native")}
                  className={cn(
                    "rounded-lg px-2.5 py-1 transition-colors cursor-pointer",
                    selectedCategory === "native"
                      ? "bg-emerald-600 text-white font-bold shadow-xs"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  Âm tự nhiên (3)
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCategory("emotion")}
                  className={cn(
                    "rounded-lg px-2.5 py-1 transition-colors cursor-pointer",
                    selectedCategory === "emotion"
                      ? "bg-amber-600 text-white font-bold shadow-xs"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  Cảm xúc (9)
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCategory("delivery")}
                  className={cn(
                    "rounded-lg px-2.5 py-1 transition-colors cursor-pointer",
                    selectedCategory === "delivery"
                      ? "bg-blue-600 text-white font-bold shadow-xs"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  Ngữ điệu (7)
                </button>
              </div>
            </div>

            {/* Tag List Grid */}
            <div className="mt-3 max-h-56 overflow-y-auto pr-1 flex flex-wrap gap-1.5">
              {filteredPaletteTags.length === 0 ? (
                <div className="w-full py-6 text-center text-xs text-muted-foreground">
                  Không tìm thấy thẻ phù hợp
                </div>
              ) : (
                filteredPaletteTags.map((tag) => {
                  const isNative = tag.type === "native"
                  const isJustClicked = recentlyInsertedId === tag.id

                  return (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() => {
                        handleSelectTag(tag)
                        setPopoverOpen(false)
                      }}
                      className={cn(
                        "group relative inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition-all duration-150 cursor-pointer select-none active:scale-95",
                        isJustClicked
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/40"
                          : isNative
                            ? "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/25"
                            : tag.type === "emotion"
                              ? "bg-amber-500/10 hover:bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/25"
                              : "bg-background hover:bg-muted text-foreground border border-border/60 hover:border-primary/40"
                      )}
                    >
                      <span className="text-sm leading-none">{tag.icon}</span>
                      <span>{tag.label}</span>
                      <span className="text-[10px] font-mono font-normal opacity-60">
                        {tag.token}
                      </span>
                    </button>
                  )
                })
              )}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Right: Keyboard shortcut hint */}
      <div className="hidden lg:flex items-center gap-1 shrink-0 text-[11px] text-muted-foreground/80 font-medium pl-2">
        <span>💡 Gõ</span>
        <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-bold text-foreground border border-border/50">
          [
        </kbd>
        <span>hoặc</span>
        <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-bold text-foreground border border-border/50">
          /
        </kbd>
        <span>để gợi ý</span>
      </div>
    </div>
  )
}
