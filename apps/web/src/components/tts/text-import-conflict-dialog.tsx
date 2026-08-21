import { useEffect } from "react";
import { FileWarning, Plus, FileSignature, X } from "lucide-react";
import { useTranslation } from "@/hooks/use-translation";

type TextImportConflictDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  fileName: string;
  onReplace: () => void;
  onAppend: () => void;
};

export function TextImportConflictDialog({
  isOpen,
  onClose,
  fileName,
  onReplace,
  onAppend,
}: TextImportConflictDialogProps) {
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

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="mb-6 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-100 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400">
              <FileWarning className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-foreground">
                {t("generate.importConflictTitle")}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {t("generate.importConflictMessage", { fileName })}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <button
            onClick={onAppend}
            className="flex w-full items-center justify-between rounded-xl bg-primary px-4 py-3.5 text-sm font-bold text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <div className="flex items-center gap-3">
              <Plus className="h-5 w-5 opacity-80" />
              <span>{t("generate.appendCurrent")}</span>
            </div>
          </button>
          
          <button
            onClick={onReplace}
            className="flex w-full items-center justify-between rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3.5 text-sm font-bold text-destructive hover:bg-destructive/10 transition-colors"
          >
            <div className="flex items-center gap-3">
              <FileSignature className="h-5 w-5 opacity-80" />
              <span>{t("generate.replaceCurrent")}</span>
            </div>
          </button>
          
          <button
            onClick={onClose}
            className="flex w-full items-center justify-center rounded-xl border border-border bg-transparent px-4 py-3.5 text-sm font-bold hover:bg-muted transition-colors mt-2 text-muted-foreground hover:text-foreground"
          >
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
