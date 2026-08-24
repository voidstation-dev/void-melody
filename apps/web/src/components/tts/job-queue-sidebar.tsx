import { useQueue } from "@/hooks/use-queue";
import { Loader2, CheckCircle2, XCircle, Clock, Play, Pause, Trash2, RotateCcw, Layers, CornerUpLeft, RefreshCw, Rewind, FastForward, Download } from "lucide-react";
import { TTSJob } from "@/types/tts-job";
import { apiFetchBlob } from "@/lib/api-client";
import { useEffect, useState, useRef } from "react";
import { AudioDownloadDialog } from "./audio-download-dialog";
import { TextPreviewDialog } from "./text-preview-dialog";
import { useTranslation } from "@/hooks/use-translation";

export function JobQueueSidebar({ onReparse }: { onReparse?: (jobText: string, fileName?: string) => void }) {
  const { queue, activeJobs, refreshQueue } = useQueue();
  const { t } = useTranslation();

  // Sort queue: processing/queued first, then completed (newest first)
  const sortedQueue = [...queue].sort((a, b) => {
    const aActive = a.status === "processing" || a.status === "queued" ? 1 : 0;
    const bActive = b.status === "processing" || b.status === "queued" ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    
    // If they belong to the same batch, sort by batchPosition ascending so the first item stays at top
    if (a.batchId && b.batchId && a.batchId === b.batchId) {
      return (a.batchPosition ?? 0) - (b.batchPosition ?? 0);
    }
    
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  if (queue.length === 0) {
    return (
      <div className="relative rounded-2xl border-2 border-dashed border-border/60 bg-card p-8 flex flex-col items-center justify-center text-center overflow-hidden min-h-[240px] group transition-colors hover:border-primary/30 mt-8">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="relative flex items-center justify-center w-14 h-14 rounded-full bg-background shadow-sm border border-border/50 mb-4 group-hover:scale-110 transition-transform duration-300">
          <Layers className="h-6 w-6 text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
        <h3 className="text-sm font-bold text-foreground mb-1.5">{t("generate.queueEmpty")}</h3>
        <p className="text-xs text-muted-foreground max-w-[200px] leading-relaxed">
          {t("generate.queueEmptyDesc")}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 flex-1 min-h-0 pt-2">
      <div className="flex items-center justify-between shrink-0 mb-1">
        <h3 className="text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">
          {t("generate.queueTitle")}
        </h3>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => refreshQueue()}
            className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title={t("generate.refreshTooltip")}
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
          <span className="text-xs font-semibold text-muted-foreground px-2 py-0.5 rounded-full bg-muted">
            {activeJobs.length} {t("generate.activeCount")}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-3 overflow-y-auto pr-1 pb-2">
        {sortedQueue.map((job) => (
          <JobItem key={job.id} job={job} onReparse={onReparse} />
        ))}
      </div>
    </div>
  );
}

function JobItem({ job, onReparse }: { job: TTSJob; onReparse?: (jobText: string, fileName?: string) => void }) {
  const { removeFromQueue, retryJob } = useQueue();
  const { t } = useTranslation();
  const [playing, setPlaying] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  const [previewOpen, setPreviewOpen] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState<"mp3" | "m4a" | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<"mp3" | "m4a" | null>(null);
  
  const seekIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const seekTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopSeeking = () => {
    if (seekTimeoutRef.current) clearTimeout(seekTimeoutRef.current);
    if (seekIntervalRef.current) clearInterval(seekIntervalRef.current);
  };

  const startSeeking = (direction: "forward" | "rewind") => {
    if (!audioRef.current || !duration) return;
    
    const jump = direction === "forward" ? 10 : -10;
    let newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + jump));
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);

    seekTimeoutRef.current = setTimeout(() => {
      seekIntervalRef.current = setInterval(() => {
        if (!audioRef.current || !duration) return;
        const step = direction === "forward" ? 2 : -2;
        let t = Math.max(0, Math.min(duration, audioRef.current.currentTime + step));
        audioRef.current.currentTime = t;
        setCurrentTime(t);
      }, 100);
    }, 400);
  };

  const sliderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const slider = sliderRef.current;
    if (!slider) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (!audioRef.current || !duration) return;

      let delta = 0;
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
        delta = e.deltaX;
      } else {
        delta = -e.deltaY;
      }
      
      const skipSeconds = (delta / 50) * 2; 
      let newTime = audioRef.current.currentTime + skipSeconds;
      newTime = Math.max(0, Math.min(newTime, duration));
      
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    };

    slider.addEventListener("wheel", handleWheel, { passive: false });
    return () => slider.removeEventListener("wheel", handleWheel);
  }, [duration]);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobUrlRef = useRef<string | null>(null);

  const formatTime = (time: number) => {
    if (isNaN(time)) return "0:00";
    const m = Math.floor(time / 60);
    const s = Math.floor(time % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const [audioSrc, setAudioSrc] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (audioBlobUrlRef.current && typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(audioBlobUrlRef.current);
      }
    };
  }, [job.audioUrl]);

  const togglePlay = async () => {
    if (playing) {
      audioRef.current?.pause();
      return;
    }

    if (!audioBlobUrlRef.current) {
      try {
        const blob = await apiFetchBlob(`/api/v1/tts/jobs/${job.id}/audio`);
        const url = URL.createObjectURL(blob);
        audioBlobUrlRef.current = url;
        setAudioSrc(url);
      } catch (err) {
        console.error("Failed to load audio blob", err);
        return;
      }
    }

    audioRef.current?.play().catch(console.error);
  };

  const handleStartDownload = async (format: "mp3" | "m4a", customFileName?: string) => {
    setDownloadingFormat(format);
    try {
      const endpoint = format === "m4a" 
        ? `/api/v1/tts/jobs/${job.id}/audio?format=m4a` 
        : `/api/v1/tts/jobs/${job.id}/audio`;
      const blob = await apiFetchBlob(endpoint);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      if (customFileName) {
        const hasExt = customFileName.toLowerCase().endsWith(`.${format}`);
        a.download = hasExt ? customFileName : `${customFileName}.${format}`;
      } else {
        const baseName = job.sourceFileName 
          ? job.sourceFileName.replace(/\.[^/.]+$/, "") 
          : `melody_${job.id.slice(0, 8)}`;
        a.download = `${baseName}.${format}`;
      }

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      if (typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Failed to download audio", err);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleDownloadClick = (format: "mp3" | "m4a") => {
    setDownloadFormat(format);
    setDownloadOpen(true);
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await removeFromQueue(job.id);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await retryJob(job.id);
    } finally {
      setIsRetrying(false);
    }
  };

  const isCustomVoice = job.providerId === "vieneu" || (job.voiceType && job.voiceType.startsWith("custom_"));

  const renderStatusBadge = () => {
    switch (job.status) {
      case "processing":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>
              {job.progress && job.progress > 0 
                ? `${t("generate.statusProcessing")} (${Math.round(job.progress)}%)` 
                : t("generate.statusProcessing")}
            </span>
          </span>
        );
      case "queued":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Clock className="h-3 w-3 animate-pulse" />
            <span>{t("generate.statusQueued")}</span>
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" />
            <span>{t("generate.statusCompleted")}</span>
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-destructive/10 text-destructive border border-destructive/20">
            <XCircle className="h-3 w-3" />
            <span>{t("generate.statusFailed")}</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col gap-2.5 rounded-2xl border border-border/70 bg-card p-3.5 shadow-xs relative overflow-visible transition-all hover:border-border hover:shadow-sm">
      {/* HEADER: Title & Actions */}
      <div className="flex items-center justify-between gap-2 relative z-30">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-xs font-bold truncate text-foreground">
              {job.voiceDisplayName || job.voiceType}
            </span>
            {isCustomVoice && (
              <span className="shrink-0 rounded-full bg-violet-500/10 px-1.5 py-0.2 text-[9px] font-bold text-violet-600 dark:text-violet-400">
                Clone
              </span>
            )}
          </div>
          {renderStatusBadge()}
        </div>

        <div className="flex items-center gap-0.5 shrink-0">
          {job.status === "failed" && (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              title={t("generate.retryJobTooltip")}
            >
              <RotateCcw className={`h-3.5 w-3.5 ${isRetrying ? "animate-spin" : ""}`} />
            </button>
          )}

          {job.status === "completed" && job.audioUrl && (
            <div className="relative group flex items-center justify-center">
              <button 
                className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-500 transition-colors"
                title={t("generate.downloadAudioTooltip")}
              >
                {downloadingFormat ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              </button>
              <div className="absolute top-full right-0 pt-1.5 opacity-0 group-hover:opacity-100 transition-all pointer-events-none group-hover:pointer-events-auto z-50">
                <div className="bg-white dark:bg-zinc-900 border border-border/80 shadow-2xl rounded-xl flex flex-col min-w-[96px] overflow-hidden p-1 ring-1 ring-black/10 dark:ring-white/10">
                  <button
                    onClick={() => handleDownloadClick("mp3")}
                    disabled={downloadingFormat !== null}
                    className="px-2.5 py-1.5 text-xs font-bold text-left rounded-lg hover:bg-muted text-foreground transition-colors disabled:opacity-50 flex items-center justify-between gap-2"
                  >
                    <span>MP3</span>
                    <span className="text-[9px] font-medium text-muted-foreground">Audio</span>
                  </button>
                  <button
                    onClick={() => handleDownloadClick("m4a")}
                    disabled={downloadingFormat !== null}
                    className="px-2.5 py-1.5 text-xs font-bold text-left rounded-lg hover:bg-muted text-foreground transition-colors disabled:opacity-50 flex items-center justify-between gap-2 mt-0.5"
                  >
                    <span>M4A</span>
                    <span className="text-[9px] font-medium text-muted-foreground">AAC</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          <button 
            onClick={() => setPreviewOpen(true)}
            className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-indigo-500/10 text-muted-foreground hover:text-indigo-500 transition-colors"
            title={t("generate.previewTextTooltip")}
          >
            <Layers className="h-3.5 w-3.5" />
          </button>
          
          <button 
            onClick={() => onReparse?.(job.text, job.sourceFileName || undefined)}
            className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-orange-500/10 text-muted-foreground hover:text-orange-500 transition-colors"
            title={t("generate.loadComposerTooltip")}
          >
            <CornerUpLeft className="h-3.5 w-3.5" />
          </button>

          <button 
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors disabled:opacity-50"
            title={t("generate.deleteJobTooltip")}
          >
            {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* CONTENT: Text Preview */}
      <div className="bg-muted/30 rounded-xl p-2.5 border border-border/40 relative z-10">
        <p className={`text-xs leading-relaxed line-clamp-2 ${job.status === "completed" ? "text-foreground font-medium" : "text-muted-foreground"}`}>
          {job.textPreview}
        </p>
      </div>

      {/* FOOTER: Audio Player */}
      {job.status === "completed" && job.audioUrl && (
        <div className="flex items-center gap-2 pt-0.5 relative z-20">
          <div className="flex-1 flex items-center gap-2 rounded-xl bg-muted/40 border border-border/50 p-1.5 pl-2 pr-3 shadow-2xs">
            {/* Control buttons */}
            <div className="flex items-center gap-1 shrink-0">
              <button
                onPointerDown={() => startSeeking("rewind")}
                onPointerUp={stopSeeking}
                onPointerLeave={stopSeeking}
                onContextMenu={(e) => e.preventDefault()}
                className="flex items-center justify-center h-6 w-6 rounded-lg bg-background border border-border/40 hover:bg-muted text-muted-foreground hover:text-foreground transition-all select-none"
                title={t("generate.rewindTooltip")}
              >
                <Rewind className="h-3 w-3" />
              </button>
              
              <button
                onClick={togglePlay}
                className={`flex items-center justify-center h-7 w-7 rounded-lg transition-all shadow-xs ${
                  playing 
                    ? "bg-primary text-primary-foreground ring-2 ring-primary/20" 
                    : "bg-primary text-primary-foreground hover:opacity-90 active:scale-95"
                }`}
                title={playing ? t("generate.pauseTooltip") : t("generate.playTooltip")}
              >
                {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 ml-0.5" />}
              </button>

              <button
                onPointerDown={() => startSeeking("forward")}
                onPointerUp={stopSeeking}
                onPointerLeave={stopSeeking}
                onContextMenu={(e) => e.preventDefault()}
                className="flex items-center justify-center h-6 w-6 rounded-lg bg-background border border-border/40 hover:bg-muted text-muted-foreground hover:text-foreground transition-all select-none"
                title={t("generate.forwardTooltip")}
              >
                <FastForward className="h-3 w-3" />
              </button>
            </div>
            
            {/* Progress Slider */}
            <div 
              ref={sliderRef}
              className="flex-1 h-2 bg-muted-foreground/15 rounded-full overflow-hidden cursor-pointer relative group/slider"
              onPointerDown={(e) => {
                if (!audioRef.current || !duration) return;
                const rect = e.currentTarget.getBoundingClientRect();
                
                const updatePosition = (clientX: number) => {
                  let percent = (clientX - rect.left) / rect.width;
                  percent = Math.max(0, Math.min(1, percent));
                  const newTime = percent * duration;
                  if (audioRef.current) audioRef.current.currentTime = newTime;
                  setCurrentTime(newTime);
                };
                
                updatePosition(e.clientX);
                
                const handlePointerMove = (moveEvent: PointerEvent) => {
                  updatePosition(moveEvent.clientX);
                };
                
                const handlePointerUp = () => {
                  window.removeEventListener("pointermove", handlePointerMove);
                  window.removeEventListener("pointerup", handlePointerUp);
                };
                
                window.addEventListener("pointermove", handlePointerMove);
                window.addEventListener("pointerup", handlePointerUp);
              }}
              title={t("generate.seekTooltip")}
            >
              <div 
                className="absolute top-0 left-0 h-full rounded-full bg-primary transition-all duration-75 ease-linear"
                style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
              />
              <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover/slider:opacity-100 transition-opacity pointer-events-none" />
            </div>
            
            {/* Time */}
            <div className="flex items-center gap-1 shrink-0 text-[10px] font-mono font-semibold text-muted-foreground tabular-nums">
              <span className="text-foreground">{formatTime(currentTime)}</span>
              <span className="text-muted-foreground/60">/</span>
              <span>{formatTime(duration || job.audioDuration || 0)}</span>
            </div>
          </div>
        </div>
      )}

      <audio 
        ref={audioRef} 
        src={audioSrc || undefined}
        onEnded={() => setPlaying(false)} 
        onPause={() => setPlaying(false)}
        onPlay={() => setPlaying(true)}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        className="hidden" 
      />

      {job.status === "failed" && (
        <div className="p-2.5 rounded-xl bg-destructive/10 border border-destructive/20 relative z-10 overflow-hidden">
          <p className="text-[11px] leading-relaxed font-medium text-destructive break-all break-words whitespace-pre-wrap max-h-28 overflow-y-auto pr-1">
            {job.errorMessage || t("errors.generic")}
          </p>
        </div>
      )}

      <TextPreviewDialog 
        isOpen={previewOpen} 
        onClose={() => setPreviewOpen(false)} 
        job={job} 
      />
      
      {downloadFormat && (
        <AudioDownloadDialog 
          isOpen={downloadOpen} 
          onClose={() => setDownloadOpen(false)} 
          job={job} 
          format={downloadFormat} 
          onStartDownload={(fileName) => {
            setDownloadOpen(false);
            handleStartDownload(downloadFormat, fileName);
          }}
        />
      )}
    </div>
  );
}
