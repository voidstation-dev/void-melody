import { useEffect } from "react";
import { X, FileText, Download } from "lucide-react";
import { TTSJob } from "@/types/tts-job";
import { getFirstLine, slugify } from "@/lib/utils";
import { useTranslation } from "@/hooks/use-translation";

type TextPreviewDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  job: TTSJob | null;
};

export function TextPreviewDialog({
  isOpen,
  onClose,
  job,
}: TextPreviewDialogProps) {
  const { t } = useTranslation();

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") onClose();
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        document.body.style.overflow = "unset";
        window.removeEventListener("keydown", handleKeyDown);
      };
    } else {
      document.body.style.overflow = "unset";
    }
  }, [isOpen, onClose]);

  if (!isOpen || !job) return null;

  const handleDownloadText = () => {
    const suggestedName = slugify(getFirstLine(job.text)) || `melody-${job.id}`;
    const blob = new Blob([job.text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${suggestedName}.txt`;
    a.click();
    if (typeof URL.revokeObjectURL === "function") {
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border border-border bg-card shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex shrink-0 items-center justify-between border-b border-border p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </div>
            <div className="flex flex-col max-w-[400px]">
              <h3 className="text-sm font-bold text-foreground">
                {t("generate.textPreview")}
              </h3>
              <p className="text-[10px] font-medium text-muted-foreground truncate">
                {job.sourceFileName ? `File: ${job.sourceFileName}` : t("generate.manualInput")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadText}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              title={t("generate.downloadText")}
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t("generate.saveTxt")}</span>
            </button>
            <div className="w-px h-4 bg-border mx-1" />
            <button 
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
          {job.text}
        </div>
        
        <div className="shrink-0 border-t border-border p-3 flex justify-between items-center text-xs text-muted-foreground bg-muted/20">
          <span>{job.text.length.toLocaleString()} {t("generate.characters")}</span>
          <span>{t("generate.voice")} {job.voiceDisplayName}</span>
        </div>
      </div>
    </div>
  );
}
