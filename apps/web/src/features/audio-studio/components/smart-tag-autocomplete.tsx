import React, { useEffect, useState, useRef, useMemo } from "react"
import { Sparkles, Zap, Check } from "lucide-react"
import { ALL_TAGS } from "../lib/delivery-tags"
import type { DeliveryTag } from "../types"
import { cn } from "@/lib/utils"

interface SmartTagAutocompleteProps {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
  text: string
  onChange: (newText: string) => void
}

// Remove Vietnamese accents / diacritics for flexible search
function removeVietnameseTones(str: string): string {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .trim()
}

export function SmartTagAutocomplete({
  textareaRef,
  text,
  onChange,
}: SmartTagAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [triggerMatch, setTriggerMatch] = useState<{ start: number; end: number; trigger: string } | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [coords, setCoords] = useState<{ top: number; left: number; isFlipped: boolean }>({
    top: 40,
    left: 20,
    isFlipped: false,
  })

  const itemRefs = useRef<(HTMLButtonElement | null)[]>([])
  const containerRef = useRef<HTMLDivElement>(null)

  // Filter matching tags with accent-insensitive & fuzzy matching
  const matchingTags = useMemo(() => {
    if (!isOpen) return []
    const rawQ = query.trim().toLowerCase()
    const normQ = removeVietnameseTones(rawQ)

    if (!rawQ) {
      // If no query yet (just typed '[' or '/'), show all tags
      return ALL_TAGS
    }

    return ALL_TAGS.filter((tag) => {
      const rawLabel = tag.label.toLowerCase()
      const normLabel = removeVietnameseTones(tag.label)
      const rawToken = tag.token.toLowerCase()
      const normToken = removeVietnameseTones(tag.token)
      const rawDesc = tag.description ? tag.description.toLowerCase() : ""
      const normDesc = tag.description ? removeVietnameseTones(tag.description) : ""
      const rawId = tag.id.toLowerCase()

      return (
        rawLabel.includes(rawQ) ||
        normLabel.includes(normQ) ||
        rawToken.includes(rawQ) ||
        normToken.includes(normQ) ||
        rawId.includes(normQ) ||
        rawDesc.includes(rawQ) ||
        normDesc.includes(normQ)
      )
    })
  }, [isOpen, query])

  // Reset or clamp selectedIndex when matching list changes
  useEffect(() => {
    setSelectedIndex((prev) => {
      if (matchingTags.length === 0) return 0
      if (prev >= matchingTags.length) return 0
      return prev
    })
  }, [matchingTags.length])

  // Scroll active item into view when navigating with Arrow keys
  useEffect(() => {
    if (isOpen && itemRefs.current[selectedIndex]) {
      itemRefs.current[selectedIndex]?.scrollIntoView({
        block: "nearest",
      })
    }
  }, [selectedIndex, isOpen])

  // Monitor cursor, typing & calculate position
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    const updateAutocompleteState = () => {
      const cursor = textarea.selectionStart
      if (cursor === null || cursor === undefined) {
        setIsOpen(false)
        return
      }

      // Check text before cursor (up to 25 chars)
      const textBefore = text.slice(0, cursor)
      const match = textBefore.match(/(?:\[|\/)([\p{L}\p{N}_\- ]{0,15})$/u)

      if (match && match.index !== undefined) {
        const triggerChar = textBefore[match.index]
        const matchQuery = match[1] || ""
        setQuery(matchQuery)
        setTriggerMatch({
          start: match.index,
          end: cursor,
          trigger: triggerChar,
        })

        // Approximate caret coordinates inside textarea
        const lines = textBefore.split("\n")
        const lineIndex = lines.length - 1
        const currentLine = lines[lineIndex] || ""
        const lineHeight = 24
        const estimatedTop = (lineIndex + 1) * lineHeight - textarea.scrollTop + 10
        const estimatedLeft = Math.min(
          Math.max(16, currentLine.length * 8 + 16),
          Math.max(20, textarea.clientWidth - 340)
        )

        // Check if popup would overflow bottom of textarea
        const popupHeight = 250
        const isNearBottom = estimatedTop + popupHeight > textarea.clientHeight
        const adjustedTop = isNearBottom
          ? Math.max(10, estimatedTop - popupHeight - lineHeight)
          : Math.max(10, Math.min(estimatedTop, textarea.clientHeight - popupHeight))

        setCoords({
          top: adjustedTop,
          left: estimatedLeft,
          isFlipped: isNearBottom,
        })
        setIsOpen(true)
      } else {
        setIsOpen(false)
      }
    }

    textarea.addEventListener("input", updateAutocompleteState)
    textarea.addEventListener("click", updateAutocompleteState)
    textarea.addEventListener("keyup", updateAutocompleteState)
    textarea.addEventListener("scroll", updateAutocompleteState)

    return () => {
      textarea.removeEventListener("input", updateAutocompleteState)
      textarea.removeEventListener("click", updateAutocompleteState)
      textarea.removeEventListener("keyup", updateAutocompleteState)
      textarea.removeEventListener("scroll", updateAutocompleteState)
    }
  }, [text, textareaRef])

  const insertSelectedTag = (tag: DeliveryTag) => {
    const textarea = textareaRef.current
    if (!textarea || !triggerMatch) return

    const before = text.slice(0, triggerMatch.start)
    const after = text.slice(triggerMatch.end)
    const replacement = `${tag.token} `
    const newText = before + replacement + after

    onChange(newText)
    setIsOpen(false)

    // Move cursor right after the inserted token
    requestAnimationFrame(() => {
      const newCursor = triggerMatch.start + replacement.length
      textarea.focus()
      textarea.setSelectionRange(newCursor, newCursor)
    })
  }

  // Keyboard navigation
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea || !isOpen || matchingTags.length === 0) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault()
        e.stopPropagation()
        setSelectedIndex((prev) => (prev + 1) % matchingTags.length)
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        e.stopPropagation()
        setSelectedIndex((prev) => (prev - 1 + matchingTags.length) % matchingTags.length)
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault()
        e.stopPropagation()
        if (matchingTags[selectedIndex]) {
          insertSelectedTag(matchingTags[selectedIndex])
        }
      } else if (e.key === "Escape") {
        e.preventDefault()
        e.stopPropagation()
        setIsOpen(false)
      }
    }

    textarea.addEventListener("keydown", handleKeyDown)
    return () => textarea.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, matchingTags, selectedIndex, text, triggerMatch])

  if (!isOpen || matchingTags.length === 0) return null

  return (
    <div
      ref={containerRef}
      style={{
        top: `${coords.top}px`,
        left: `${coords.left}px`,
      }}
      className="absolute z-50 w-72 sm:w-80 rounded-2xl border border-border/80 bg-card/98 p-1.5 text-card-foreground shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100 ring-1 ring-black/10 dark:ring-white/10"
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-2.5 py-1 text-[11px] font-bold text-muted-foreground border-b border-border/50 mb-1">
        <span className="flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-primary" />
          <span>Gợi ý ({matchingTags.length})</span>
        </span>
        <span className="text-[10px] font-mono opacity-60">↑↓ chọn · Enter chèn</span>
      </div>

      {/* Scrollable list of tags */}
      <div className="max-h-56 overflow-y-auto custom-scrollbar space-y-0.5 pr-0.5">
        {matchingTags.map((tag, idx) => {
          const isSelected = idx === selectedIndex
          const isNative = tag.type === "native"

          return (
            <button
              key={tag.id}
              ref={(el) => {
                itemRefs.current[idx] = el
              }}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault()
                insertSelectedTag(tag)
              }}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={cn(
                "flex w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-left text-xs font-semibold transition-colors cursor-pointer select-none",
                isSelected
                  ? "bg-primary text-primary-foreground font-bold shadow-xs scale-[1.01]"
                  : "text-foreground hover:bg-muted/60"
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-base leading-none shrink-0">{tag.icon}</span>
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold leading-tight">{tag.label}</p>
                  <p
                    className={cn(
                      "text-[10px] font-mono truncate font-normal leading-tight mt-0.5",
                      isSelected ? "text-primary-foreground/80" : "text-muted-foreground"
                    )}
                  >
                    {tag.token}
                  </p>
                </div>
              </div>

              <span
                className={cn(
                  "shrink-0 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md ml-1",
                  isSelected
                    ? "bg-primary-foreground/20 text-primary-foreground"
                    : isNative
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : tag.type === "emotion"
                        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                        : "bg-muted text-muted-foreground"
                )}
              >
                {isNative ? "VieNeu" : tag.type === "emotion" ? "Cảm xúc" : "Ngữ điệu"}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
