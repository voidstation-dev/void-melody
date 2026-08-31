import { useState, useMemo } from "react"
import { useThemePalette } from "@/contexts/theme-palette-provider"
import { useTranslation } from "@/hooks/use-translation"
import { Input } from "@/components/ui/input"
import { Search, Shuffle, Check, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ThemeCategory } from "@/lib/themes/theme-types"

interface CategoryOption {
  id: ThemeCategory
  labelVi: string
  labelEn: string
}

const CATEGORIES: CategoryOption[] = [
  { id: "all", labelVi: "Tất cả", labelEn: "All" },
  { id: "studio", labelVi: "Studio & Tối giản", labelEn: "Studio" },
  { id: "cyber", labelVi: "Cyber & Tech", labelEn: "Cyber & Tech" },
  { id: "nature", labelVi: "Tự nhiên", labelEn: "Nature" },
  { id: "pastel", labelVi: "Pastel & Mềm mại", labelEn: "Pastel" },
  { id: "classic", labelVi: "Cổ điển & Vintage", labelEn: "Classic" },
]

export function ThemePalettePicker() {
  const { activeThemeId, setThemeId, shuffleTheme, allThemes } = useThemePalette()
  const { locale } = useTranslation()
  const isVi = locale === "vi"

  const [search, setSearch] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<ThemeCategory>("all")

  const filteredThemes = useMemo(() => {
    return allThemes.filter((theme) => {
      const matchCategory = selectedCategory === "all" || theme.category === selectedCategory
      const matchSearch =
        !search.trim() ||
        theme.name.toLowerCase().includes(search.toLowerCase()) ||
        theme.descriptionVi.toLowerCase().includes(search.toLowerCase()) ||
        theme.descriptionEn.toLowerCase().includes(search.toLowerCase())
      return matchCategory && matchSearch
    })
  }, [allThemes, selectedCategory, search])

  return (
    <div className="space-y-4">
      {/* Search & Actions Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={isVi ? "Tìm kiếm theme màu..." : "Search theme palettes..."}
            className="pl-9 h-9 text-xs sm:text-sm rounded-xl bg-background/60"
          />
        </div>

        <button
          type="button"
          onClick={shuffleTheme}
          className="flex items-center justify-center gap-1.5 h-9 px-3.5 rounded-xl border border-border/80 bg-background/80 hover:bg-muted text-xs font-semibold text-foreground transition-all shrink-0 cursor-pointer shadow-2xs hover:scale-102 active:scale-98"
          title={isVi ? "Đổi theme ngẫu nhiên" : "Shuffle random theme"}
        >
          <Shuffle className="h-3.5 w-3.5 text-primary" />
          <span>{isVi ? "Đổi ngẫu nhiên" : "Shuffle"}</span>
        </button>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {CATEGORIES.map((cat) => {
          const isActive = selectedCategory === cat.id
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id)}
              className={cn(
                "whitespace-nowrap px-3 py-1 text-[11px] font-semibold rounded-lg transition-all cursor-pointer",
                isActive
                  ? "bg-primary text-primary-foreground shadow-2xs"
                  : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {isVi ? cat.labelVi : cat.labelEn}
            </button>
          )
        })}
      </div>

      {/* Theme Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[380px] overflow-y-auto pr-1">
        {filteredThemes.map((theme) => {
          const isActive = activeThemeId === theme.id
          return (
            <button
              key={theme.id}
              type="button"
              onClick={() => setThemeId(theme.id)}
              className={cn(
                "flex items-start justify-between gap-3 p-3 rounded-xl border text-left transition-all cursor-pointer relative group",
                isActive
                  ? "border-primary bg-primary/10 ring-1 ring-primary/30 shadow-xs"
                  : "border-border/70 bg-card hover:border-border hover:bg-muted/40",
              )}
            >
              <div className="min-w-0 flex-1">
                {/* 4-Color Swatch Palette */}
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className="flex items-center -space-x-1 p-0.5 rounded-full bg-muted/60 border border-border/40">
                    {theme.palette.map((color, idx) => (
                      <span
                        key={idx}
                        className="h-3.5 w-3.5 rounded-full ring-1 ring-background shadow-2xs shrink-0"
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                  <span className="font-bold text-xs text-foreground truncate">
                    {theme.name}
                  </span>
                  {theme.id === "default" && (
                    <span className="rounded bg-amber-500/15 px-1 py-0.2 text-[9px] font-black uppercase text-amber-600 dark:text-amber-400">
                      Studio
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-muted-foreground line-clamp-1 leading-snug">
                  {isVi ? theme.descriptionVi : theme.descriptionEn}
                </p>
              </div>

              {isActive && (
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-2xs">
                  <Check className="h-3 w-3 stroke-[3]" />
                </div>
              )}
            </button>
          )
        })}

        {filteredThemes.length === 0 && (
          <div className="col-span-full py-8 text-center text-xs text-muted-foreground">
            {isVi ? "Không tìm thấy theme nào phù hợp." : "No themes matching your query."}
          </div>
        )}
      </div>
    </div>
  )
}
