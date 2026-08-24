import { useState, useEffect } from "react";
import { Download, X, FileAudio, Folder, Plus, User, Gauge } from "lucide-react";
import { getFirstLine, slugify } from "@/lib/utils";
import { TTSJob } from "@/types/tts-job";
import { useTauri } from "@/contexts/tauri-provider";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { downloadDir, join } from "@tauri-apps/api/path";
import { useTranslation } from "@/hooks/use-translation";

type AudioDownloadDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  job: TTSJob | null;
  format: "mp3" | "m4a";
  onStartDownload: (fileNameOrPath: string) => void;
};

export function AudioDownloadDialog({
  isOpen,
  onClose,
  job,
  format,
  onStartDownload,
}: AudioDownloadDialogProps) {
  const { t } = useTranslation();
  const [fileName, setFileName] = useState("");
  const { isDesktop } = useTauri();
  const [exportPath, setExportPath] = useState<string>("");

  useEffect(() => {
    if (isDesktop && isOpen && !exportPath) {
      downloadDir().then(dir => setExportPath(dir)).catch(console.error);
    }
  }, [isDesktop, isOpen, exportPath]);

  const handleSelectFolder = async () => {
    if (!isDesktop) return;
    try {
      const selected = await openDialog({
        directory: true,
        multiple: false,
        defaultPath: exportPath || undefined,
        title: t("generate.saveLocation")
      });
      if (selected && typeof selected === "string") {
        setExportPath(selected);
      }
    } catch (err) {
      console.error("Failed to select folder", err);
    }
  };

  useEffect(() => {
    if (isOpen && job) {
      const suggestedName = slugify(getFirstLine(job.text)) || `melody-${job.id.slice(0, 8)}`;
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFileName(suggestedName);
    }
  }, [isOpen, job]);

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

  const handleDownload = async () => {
    if (!fileName.trim()) return;
    if (isDesktop && exportPath) {
      try {
        const fullPath = await join(exportPath, `${fileName.trim()}.${format}`);
        onStartDownload(fullPath);
      } catch (err) {
        console.error("Failed to join path", err);
        onStartDownload(fileName.trim()); // Fallback
      }
    } else {
      onStartDownload(fileName.trim());
    }
  };

  const appendToFileName = (suffix: string) => {
    setFileName((prev) => {
      const cleanPrev = prev.replace(/[-_]+$/, "");
      const cleanSuffix = suffix.replace(/^[-_]+/, "");
      return cleanPrev ? `${cleanPrev}-${cleanSuffix}` : cleanSuffix;
    });
  };

  const isUUID = (str?: string | null) =>
    Boolean(str && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str));

  const isCustomVoice = Boolean(
    job.voiceType &&
      (job.voiceType.startsWith("custom_") || isUUID(job.voiceType))
  );
  const isVieneuPreset = !isCustomVoice && job.providerId === "vieneu";

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-3xl border border-border/80 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 text-primary shadow-xs">
              <FileAudio className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-foreground">
                  {t("generate.downloadAudio")}
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase rounded-full bg-primary/10 text-primary border border-primary/20 tracking-wider">
                  {format}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("generate.downloadNotice")}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Metadata summary pill bar */}
        <div className="flex items-center gap-2 p-2.5 rounded-2xl bg-muted/40 border border-border/50 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <User className="h-3.5 w-3.5 text-primary" />
            <span className="font-semibold text-foreground truncate max-w-[140px]">
              {job.voiceDisplayName || job.voiceType}
            </span>
            {isCustomVoice ? (
              <span className="rounded-full bg-violet-500/15 px-1.5 py-0.2 text-[9px] font-bold text-violet-600 dark:text-violet-400">
                Clone
              </span>
            ) : isVieneuPreset ? (
              <span className="rounded-full bg-emerald-500/15 px-1.5 py-0.2 text-[9px] font-bold text-emerald-600 dark:text-emerald-400">
                VieNeu
              </span>
            ) : null}
          </div>
          <div className="h-3 w-[1px] bg-border/80 mx-1" />
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Gauge className="h-3.5 w-3.5 text-primary" />
            <span className="font-semibold text-foreground">
              {job.rate ? `${job.rate.toFixed(1)}x` : "1.0x"}
            </span>
          </div>
        </div>

        {/* Form Inputs */}
        <div className="flex flex-col gap-4">
          {/* File Name */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between px-0.5">
              <label className="text-xs font-semibold text-foreground">
                {t("generate.fileName")}
              </label>
              <span className="text-[11px] font-mono text-muted-foreground">
                .{format}
              </span>
            </div>
            
            <div className="relative flex items-center">
              <input
                type="text"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                className="w-full rounded-2xl border border-border bg-background px-4 py-2.5 text-sm font-medium outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/15 pr-14 shadow-2xs"
                placeholder="audio-filename"
                autoFocus
              />
              <span className="absolute right-3.5 px-2 py-0.5 rounded-lg bg-muted text-[11px] font-mono font-bold text-muted-foreground pointer-events-none">
                .{format}
              </span>
            </div>

            {/* Append Quick Tags */}
            <div className="flex items-center gap-2 pt-0.5 px-0.5 flex-wrap">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t("generate.appendLabel")}
              </span>
              <button
                type="button"
                onClick={() => appendToFileName(slugify(job.voiceDisplayName || job.voiceType))}
                className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-primary/5 hover:bg-primary/15 text-primary border border-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Plus className="h-3 w-3" />
                <span>{t("generate.voiceName")}</span>
              </button>
              <button
                type="button"
                onClick={() => appendToFileName(`${job.rate?.toFixed(1) || "1.0"}x`)}
                className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-primary/5 hover:bg-primary/15 text-primary border border-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Plus className="h-3 w-3" />
                <span>{t("generate.speed")}</span>
              </button>
            </div>
          </div>

          {/* Destination Folder */}
          {isDesktop && (
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-foreground px-0.5">
                {t("generate.saveLocation")}
              </label>
              <div className="flex items-center gap-2 rounded-2xl border border-border bg-background p-1.5 pl-3 shadow-2xs">
                <Folder className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="flex-1 text-xs text-muted-foreground truncate font-mono" title={exportPath}>
                  {exportPath || t("generate.loadingDir")}
                </span>
                <button
                  type="button"
                  onClick={handleSelectFolder}
                  className="px-3 py-1.5 bg-secondary text-secondary-foreground rounded-xl text-xs font-bold hover:bg-secondary/80 transition-all shrink-0"
                >
                  {t("generate.changeVoice")}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-border/40">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground rounded-xl transition-all"
          >
            {t("common.cancel")}
          </button>

          <button
            type="button"
            onClick={handleDownload}
            disabled={!fileName.trim() || (isDesktop && !exportPath)}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all shadow-xs hover:shadow-sm active:scale-[0.98]"
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t("generate.startDownload")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
