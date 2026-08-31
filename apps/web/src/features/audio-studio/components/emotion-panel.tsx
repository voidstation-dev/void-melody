import { useState, useMemo } from "react"
import { Sparkles, Smile, Search, Sliders, Music, Zap, X } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { EmotionTag } from "./emotion-tag"
import { NATIVE_CUES, EMOTION_TAGS, ADVANCED_DELIVERY_TAGS, ALL_TAGS } from "../lib/delivery-tags"
import { useTranslation } from "@/hooks/use-translation"
import { cn } from "@/lib/utils"

interface EmotionPanelProps {
  onInsertTag: (token: string) => void
}

type TabCategory = "all" | "native" | "emotion" | "delivery"

export function EmotionPanel({ onInsertTag }: EmotionPanelProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabCategory>("all")
  const [searchQuery, setSearchQuery] = useState("")

  const filteredTags = useMemo(() => {
    let list = ALL_TAGS
    if (activeTab !== "all") {
      list = list.filter((tag) => tag.type === activeTab)
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim()
      list = list.filter(
        (tag) =>
          tag.label.toLowerCase().includes(q) ||
          tag.token.toLowerCase().includes(q) ||
          tag.description?.toLowerCase().includes(q),
      )
    }
    return list
  }, [activeTab, searchQuery])

  const categories = [
    { id: "all" as TabCategory, label: "Tất cả", count: ALL_TAGS.length, icon: Sparkles },
    { id: "native" as TabCategory, label: "Âm thanh tự nhiên", count: NATIVE_CUES.length, icon: Music, color: "text-emerald-600 dark:text-emerald-400" },
    { id: "emotion" as TabCategory, label: "Cảm xúc", count: EMOTION_TAGS.length, icon: Smile, color: "text-amber-600 dark:text-amber-400" },
    { id: "delivery" as TabCategory, label: "Ngữ điệu", count: ADVANCED_DELIVERY_TAGS.length, icon: Sliders, color: "text-sky-600 dark:text-sky-400" },
  ]

  return (
    <Card className="border-border/70 bg-card/60 backdrop-blur-md shadow-xs overflow-hidden">
      <CardHeader className="pb-3 border-b border-border/40 p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/20 to-primary/20 text-amber-600 dark:text-amber-400 border border-amber-500/20 shadow-2xs">
              <Smile className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-foreground">
                  {t("audioStudio.emotionTitle")}
                </h3>
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary border border-primary/20">
                  <Zap className="h-2.5 w-2.5" />
                  {ALL_TAGS.length} tags
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("audioStudio.emotionDesc")}
              </p>
            </div>
          </div>

          {/* Quick Search */}
          <div className="relative w-full sm:w-48">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm thẻ…"
              className="h-8 w-full rounded-xl border border-border/60 bg-background/80 pl-8 pr-7 text-xs text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>

        {/* Category Filter Tabs */}
        <div className="flex items-center gap-1.5 pt-3 overflow-x-auto custom-scrollbar no-scrollbar">
          {categories.map((cat) => {
            const Icon = cat.icon
            const isActive = activeTab === cat.id
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setActiveTab(cat.id)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer whitespace-nowrap",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-2xs font-bold"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground border border-transparent hover:border-border/40",
                )}
              >
                <Icon className={cn("h-3 w-3", !isActive && cat.color)} />
                <span>{cat.label}</span>
                <span
                  className={cn(
                    "text-[10px] px-1 py-0.2 rounded-md font-mono",
                    isActive
                      ? "bg-primary-foreground/20 text-primary-foreground"
                      : "bg-background/80 text-muted-foreground",
                  )}
                >
                  {cat.count}
                </span>
              </button>
            )
          })}
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-4">
        {/* If searching or filtering specific category */}
        {searchQuery || activeTab !== "all" ? (
          <div>
            {filteredTags.length === 0 ? (
              <div className="py-6 text-center text-xs text-muted-foreground">
                Không tìm thấy thẻ cảm xúc nào khớp với từ khóa &ldquo;{searchQuery}&rdquo;.
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {filteredTags.map((tag) => (
                  <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
                ))}
              </div>
            )}
          </div>
        ) : (
          /* Grouped "All" View */
          <div className="space-y-4">
            {/* Native Cues Section */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>{t("audioStudio.nativeCueHeading")}</span>
                </div>
                <span className="text-[10px] font-semibold text-emerald-600/80 dark:text-emerald-400/80 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  VieNeu AI Native
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {NATIVE_CUES.map((tag) => (
                  <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
                ))}
              </div>
            </div>

            {/* Emotion Nuances Section */}
            <div className="space-y-2 pt-2 border-t border-border/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  <Smile className="h-3.5 w-3.5" />
                  <span>{t("audioStudio.emotionHeading")}</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {EMOTION_TAGS.map((tag) => (
                  <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
                ))}
              </div>
            </div>

            {/* Delivery Nuances Section */}
            <div className="space-y-2 pt-2 border-t border-border/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-sky-600 dark:text-sky-400">
                  <Sliders className="h-3.5 w-3.5" />
                  <span>{t("audioStudio.deliveryTitle")}</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {ADVANCED_DELIVERY_TAGS.map((tag) => (
                  <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
                ))}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
