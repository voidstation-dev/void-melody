import React, { useState } from "react"
import { FileText, Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { ImportToolbar } from "./import-toolbar"
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
        "relative flex flex-col flex-1 min-h-[360px] lg:min-h-[440px] border-border/80 shadow-sm transition-all duration-200",
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
        <div className="relative flex-1 min-h-[220px] w-full pt-3">
          {!hasText && (
            <div className="pointer-events-none absolute inset-0 text-sm sm:text-base leading-relaxed text-muted-foreground/40 select-none pt-3">
              <p className="font-semibold text-foreground/50">
                Nhập hoặc dán nội dung kịch bản vào đây…
              </p>
              <p className="mt-1 text-xs text-muted-foreground/60 leading-normal">
                Mẹo: Bạn có thể chọn các thẻ cảm xúc bên dưới như <code className="text-emerald-600 dark:text-emerald-400 font-mono font-bold">[cười]</code>,{" "}
                <code className="text-amber-600 dark:text-amber-400 font-mono font-bold">[bình tĩnh]</code> hoặc kéo thả file TXT/SRT trực tiếp vào đây.
              </p>
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            maxLength={500000}
            className="h-full min-h-[220px] w-full resize-none bg-transparent text-sm sm:text-base leading-relaxed text-foreground focus:outline-none disabled:opacity-50 font-normal custom-scrollbar"
            placeholder=""
            autoFocus
          />
        </div>

        {/* Footer Counters */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/40 pt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="font-semibold">{segmentCount} đoạn văn</span>
            {cueCount > 0 && (
              <span className="flex items-center gap-1 font-semibold text-primary">
                <Sparkles className="h-3 w-3" />
                {cueCount} thẻ cảm xúc
              </span>
            )}
          </div>
          <div className="font-mono text-[11px] font-semibold text-muted-foreground/80">
            {characterCount.toLocaleString()} / 500,000 ký tự
          </div>
        </div>

        {/* Drag Overlay */}
        {isDragging && (
          <div className="pointer-events-none absolute inset-0 z-50 flex flex-col items-center justify-center rounded-2xl bg-background/80 backdrop-blur-xs">
            <FileText className="h-12 w-12 text-primary animate-bounce mb-2" />
            <h3 className="text-base font-bold text-foreground">Thả file TXT / SRT vào đây</h3>
            <p className="text-xs text-muted-foreground mt-1">Nội dung sẽ được tự động nạp vào kịch bản</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
