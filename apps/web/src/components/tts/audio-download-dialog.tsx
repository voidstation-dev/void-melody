import { useState, useEffect } from "react";
import { Download, X, FileAudio } from "lucide-react";
import { getFirstLine, slugify } from "@/lib/utils";
import { TTSJob } from "@/types/tts-job";
import { useTauri } from "@/contexts/tauri-provider";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { downloadDir, join } from "@tauri-apps/api/path";

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
        title: "Select Download Directory"
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
      const suggestedName = slugify(getFirstLine(job.text)) || `melody-${job.id}`;
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

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="mb-5 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <FileAudio className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Download Audio</h3>
              <p className="text-xs text-muted-foreground mt-0.5 text-orange-500/80">
                You can close this popup during download
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

        <div className="mb-6 flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-xs font-medium text-muted-foreground ml-1">File Name</label>
            <div className="relative flex items-center">
              <input
                type="text"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none transition-colors focus:border-primary pr-12"
                placeholder="audio-filename"
                autoFocus
              />
              <span className="absolute right-4 text-sm text-muted-foreground pointer-events-none">
                .{format}
              </span>
            </div>
            {job && (
              <div className="flex items-center gap-2 ml-1 mt-0.5">
                <span className="text-[10px] text-muted-foreground">Append:</span>
                <button
                  onClick={() => setFileName(prev => `${prev}_${slugify(job.voiceDisplayName || job.voiceType)}`)}
                  className="text-[10px] font-medium px-2 py-1 rounded-md bg-muted hover:bg-primary/10 hover:text-primary transition-colors border border-border/50"
                >
                  + Voice Name
                </button>
                <button
                  onClick={() => setFileName(prev => `${prev}_${job.rate?.toFixed(1) || "1.0"}x`)}
                  className="text-[10px] font-medium px-2 py-1 rounded-md bg-muted hover:bg-primary/10 hover:text-primary transition-colors border border-border/50"
                >
                  + Speed
                </button>
              </div>
            )}
          </div>

          {isDesktop && (
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-muted-foreground ml-1">Location</label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={exportPath || ""}
                  className="flex-1 rounded-xl border border-border bg-background px-4 py-2.5 text-sm text-foreground focus:outline-none opacity-80"
                />
                <button
                  onClick={handleSelectFolder}
                  className="px-4 py-2.5 bg-secondary text-secondary-foreground rounded-xl text-sm font-bold hover:brightness-110 transition-all border border-border/50"
                >
                  Change
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <button
            onClick={handleDownload}
            disabled={!fileName.trim() || (isDesktop && !exportPath)}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
          >
            <Download className="h-4 w-4" />
            <span>Start Download</span>
          </button>
          
          <button
            onClick={onClose}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-muted/50 px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-muted hover:text-foreground transition-all"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
