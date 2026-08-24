import { useRef } from "react"
import { Clipboard, FileUp, FolderOpen, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { toast } from "sonner"
import { useTranslation } from "@/hooks/use-translation"

interface ImportToolbarProps {
  onPasteText: (text: string) => void
  onImportFile: (file: File) => void
  onImportFolder?: (files: FileList) => void
  onClearText: () => void
  hasText: boolean
}

export function ImportToolbar({
  onPasteText,
  onImportFile,
  onImportFolder,
  onClearText,
  hasText,
}: ImportToolbarProps) {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)

  const handleClipboardPaste = async () => {
    try {
      const clipboardText = await navigator.clipboard.readText()
      if (clipboardText.trim()) {
        onPasteText(clipboardText)
        toast.success(t("audioStudio.pasteSuccess"))
      } else {
        toast.error(t("audioStudio.clipboardEmpty"))
      }
    } catch {
      toast.error(t("audioStudio.clipboardError"))
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      onImportFile(files[0])
    }
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0 && onImportFolder) {
      onImportFolder(files)
    }
    if (folderInputRef.current) folderInputRef.current.value = ""
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3">
      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.srt,.md"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={folderInputRef}
        type="file"
        // @ts-expect-error - webkitdirectory standard non-ts prop
        webkitdirectory="true"
        directory=""
        multiple
        className="hidden"
        onChange={handleFolderChange}
      />

      <div className="flex flex-wrap items-center gap-1.5">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleClipboardPaste}
          className="h-8 gap-1.5 rounded-xl text-xs font-semibold"
        >
          <Clipboard className="h-3.5 w-3.5" />
          <span>{t("audioStudio.pasteQuick")}</span>
        </Button>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          className="h-8 gap-1.5 rounded-xl text-xs font-semibold"
        >
          <FileUp className="h-3.5 w-3.5" />
          <span>{t("audioStudio.importFile")}</span>
        </Button>

        {onImportFolder && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => folderInputRef.current?.click()}
            className="h-8 gap-1.5 rounded-xl text-xs font-semibold hidden sm:inline-flex"
          >
            <FolderOpen className="h-3.5 w-3.5" />
            <span>{t("audioStudio.importFolder")}</span>
          </Button>
        )}
      </div>

      {hasText && (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClearText}
                className="h-8 gap-1.5 rounded-xl text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>{t("audioStudio.clearText")}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" className="text-xs">
              {t("audioStudio.clearTooltip")}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  )
}
