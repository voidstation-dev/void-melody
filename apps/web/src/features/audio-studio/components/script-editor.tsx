import React, { useState } from "react"
import { FileText, Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { ImportToolbar } from "./import-toolbar"
import { SmartTagAutocomplete } from "./smart-tag-autocomplete"
import { useTranslation } from "@/hooks/use-translation"
import { cn } from "@/lib/utils"

interface ScriptEditorProps {
  text: string
  onChange: (value: string) => void
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
  characterCount: number
  segmentCount: number
  cueCount: number
  disabled?: boolean
  onImportFile: (file: File) => void
  onImportFolder?: (files: FileList) => void
  onClearText: () => void
}

export function ScriptEditor({
  text,
  onChange,
  textareaRef,
  characterCount,
  segmentCount,
  cueCount,
  disabled,
  onImportFile,
  onImportFolder,
  onClearText,
}: ScriptEditorProps) {
  const { t } = useTranslation()
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      onImportFile(files[0])
    }
  }

  const hasText = text.length > 0

  return (
    <Card
      className={cn(
        "relative flex flex-col flex-1 min-h-[360px] lg:min-h-[440px] border-border/80 shadow-sm transition-all duration-200 overflow-hidden",
        isDragging && "border-primary ring-2 ring-primary/20 bg-primary/5",
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <CardContent className="flex flex-col flex-1 p-4 sm:p-5">
        {/* Import Toolbar */}
        <ImportToolbar
          onPasteText={(pasted) => {
            if (text.trim()) {
              onChange(`${text}\n${pasted}`)
            } else {
              onChange(pasted)
            }
          }}
          onImportFile={onImportFile}
          onImportFolder={onImportFolder}
          onClearText={onClearText}
          hasText={hasText}
        />

        {/* Editor Area */}
        <div className="relative flex-1 min-h-[260px] lg:min-h-[320px] w-full my-2">
          {!hasText && (
            <div className="pointer-events-none absolute inset-0 text-sm sm:text-base leading-relaxed text-muted-foreground/40 select-none p-1">
              <p className="font-semibold text-foreground/50">
                {t("audioStudio.editorPlaceholderTitle")}
              </p>
              <p className="mt-1 text-xs text-muted-foreground/60 leading-normal">
                {t("audioStudio.editorPlaceholderHint")}
              </p>
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            maxLength={500000}
            className="absolute inset-0 h-full w-full resize-none bg-transparent text-sm sm:text-base leading-relaxed text-foreground focus:outline-none disabled:opacity-50 font-normal custom-scrollbar p-1 pb-8"
            placeholder=""
            autoFocus
          />

          {/* Autocomplete dropdown when user types '[' or '/' */}
          <SmartTagAutocomplete
            textareaRef={textareaRef}
            text={text}
            onChange={onChange}
          />
        </div>

        {/* Footer Counters & Shortcut Hint */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/40 pt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="font-semibold">{t("audioStudio.segmentCount", { count: segmentCount })}</span>
            {cueCount > 0 && (
              <span className="flex items-center gap-1 font-semibold text-primary">
                <Sparkles className="h-3 w-3" />
                {t("audioStudio.cueCount", { count: cueCount })}
              </span>
            )}
            <div className="hidden sm:flex items-center gap-1 text-[11px] text-muted-foreground/75 font-medium pl-2 border-l border-border/50">
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
          <div className="font-mono text-[11px] font-semibold text-muted-foreground/80">
            {t("audioStudio.charCount", { count: characterCount.toLocaleString() })}
          </div>
        </div>

        {/* Drag Overlay */}
        {isDragging && (
          <div className="pointer-events-none absolute inset-0 z-50 flex flex-col items-center justify-center rounded-2xl bg-background/80 backdrop-blur-xs">
            <FileText className="h-12 w-12 text-primary animate-bounce mb-2" />
            <h3 className="text-base font-bold text-foreground">{t("audioStudio.dropFileTitle")}</h3>
            <p className="text-xs text-muted-foreground mt-1">{t("audioStudio.dropFileDesc")}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
