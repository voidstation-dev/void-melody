"use client";
import { useQueue } from "@/hooks/use-queue";
import { Loader2, CheckCircle2, XCircle, Clock, Play, Pause, Trash2, RotateCcw, Layers, CornerUpLeft, RefreshCw, Rewind, FastForward, Download } from "lucide-react";
import { TTSJob } from "@/types/tts-job";
import { apiFetchBlob } from "@/lib/api-client";
import { useEffect, useState, useRef } from "react";
import { AudioDownloadDialog } from "./audio-download-dialog";
import { TextPreviewDialog } from "./text-preview-dialog";

export function JobQueueSidebar({ onReparse }: { onReparse?: (jobText: string, fileName?: string) => void }) {
  const { queue, activeJobs, completedJobs, refreshQueue } = useQueue();

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
        <h3 className="text-sm font-bold text-foreground mb-1.5">Queue is empty</h3>
        <p className="text-xs text-muted-foreground max-w-[200px] leading-relaxed">
          Submit a job from the playground to see the generation progress here.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 flex-1 min-h-0 pt-2">
      <div className="flex items-center justify-between shrink-0 mb-1">
        <h3 className="text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">QUEUE</h3>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => refreshQueue()}
            className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh Queue"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
          <span className="text-xs font-medium text-muted-foreground px-2 py-0.5 rounded-full bg-muted">
            {activeJobs.length} active
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
    
    // Immediate jump (10s)
    const jump = direction === "forward" ? 10 : -10;
    let newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + jump));
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);

    // Wait 400ms before continuous seeking
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
      e.preventDefault(); // Prevent page scrolling
      if (!audioRef.current || !duration) return;

      let delta = 0;
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
        delta = e.deltaX; // scroll right -> forward
      } else {
        delta = -e.deltaY; // scroll up (negative deltaY) -> forward
      }
      
      // Map 50 pixels of scroll to roughly 2 seconds of seeking
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

  useEffect(() => {
    return () => {
      if (audioBlobUrlRef.current) URL.revokeObjectURL(audioBlobUrlRef.current);
    };
  }, [job.audioUrl]);

  const togglePlay = async () => {
    if (playing) {
      audioRef.current?.pause();
      return;
    }
    if (!audioRef.current || !job.audioUrl) return;
    if (!audioBlobUrlRef.current) {
      const blob = await apiFetchBlob(job.audioUrl);
      const objectUrl = URL.createObjectURL(blob);
      if (!audioRef.current) {
        URL.revokeObjectURL(objectUrl);
        return;
      }
      const currentAudio = audioRef.current;
      audioBlobUrlRef.current = objectUrl;
      if (currentAudio) {
        // eslint-disable-next-line react-hooks/immutability
        currentAudio.src = objectUrl;
      }
    }
    await audioRef.current.play();
  };

  const handleDownloadClick = (format: "mp3" | "m4a") => {
    setDownloadFormat(format);
    setDownloadOpen(true);
  };

  const handleStartDownload = async (format: "mp3" | "m4a", pathOrName: string) => {
    if (!job.downloadUrl || !pathOrName.trim()) return;
    setDownloadingFormat(format);
    try {
      // If pathOrName contains a path separator, it's an absolute path from Tauri dialog
      if (pathOrName.includes("/") || pathOrName.includes("\\")) {
        const { exportJobAudio } = await import("@/lib/api-client");
        await exportJobAudio(job.id, format, pathOrName);
      } else {
        // Fallback for Web/Browser
        const blob = await apiFetchBlob(`${job.downloadUrl}?format=${format}`);
        const finalFileName = `${pathOrName.trim()}.${format}`;
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = finalFileName;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        }, 100);
      }
    } catch (err) {
      console.error("Download/Export failed:", err);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    await removeFromQueue(job.id);
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    await retryJob(job.id);
    setIsRetrying(false);
  };

  return (
    <div className={`shrink-0 relative rounded-xl border p-3 flex flex-col gap-2.5 transition-all duration-300 ${
      job.status === "completed" ? "bg-primary/[0.02] border-primary/20 shadow-sm" : 
      job.status === "processing" ? "bg-background border-primary/30 shadow-md shadow-primary/5" :
      job.status === "failed" ? "bg-destructive/[0.02] border-destructive/20" :
      "bg-background border-border"
    }`}>
      {/* Subtle background progress bar for processing */}
      {job.status === "processing" && (
        <div className="absolute inset-0 pointer-events-none rounded-xl overflow-hidden z-10">
          <div 
            className="absolute bottom-0 left-0 h-[2px] bg-primary transition-all duration-500 ease-out"
            style={{ width: `${job.progress ?? 0}%` }}
          />
        </div>
      )}

      {/* HEADER: Badges and Actions */}
      <div className="flex items-center justify-between gap-2 relative z-30">
        <div className="flex items-center gap-1.5 flex-wrap">
          <div className={`flex items-center justify-center px-1.5 h-5 rounded-[4px] text-[9px] font-extrabold tracking-wider uppercase border shadow-sm ${
            job.status === "completed" ? "bg-green-500/10 text-green-600 border-green-500/20" :
            job.status === "failed" ? "bg-red-500/10 text-red-600 border-red-500/20" :
            job.status === "processing" ? "bg-primary/10 text-primary border-primary/20" :
            "bg-muted/50 text-muted-foreground border-border/50"
          }`}>
            {job.status === "processing" && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
            {job.status}
            {job.status === "processing" && job.progress !== null && job.progress !== undefined && (
              <span className="ml-1 opacity-80 tracking-normal font-bold">· {job.progress}%</span>
            )}
          </div>
          
          <span className="rounded-[4px] bg-primary/10 px-1.5 py-0.5 text-[9px] font-bold text-primary border border-primary/20">
            {job.rate?.toFixed(1) || "1.0"}x
          </span>

          <span className="rounded-[4px] bg-muted/50 px-1.5 py-0.5 text-[9px] font-bold text-muted-foreground border border-border/50 truncate max-w-[120px]" title={job.voiceDisplayName || job.voiceType}>
            {job.voiceDisplayName || job.voiceType}
          </span>

          {(job.status === "completed" || job.status === "failed") && job.startedAt && (job.completedAt || job.updatedAt) && (
            <span className="text-[9px] font-medium text-muted-foreground/60 flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" />
              {(() => {
                const start = new Date(job.startedAt).getTime();
                const end = new Date(job.completedAt || job.updatedAt).getTime();
                const diff = Math.max(0, Math.round((end - start) / 1000));
                if (diff < 60) return `${diff}s`;
                return `${Math.floor(diff / 60)}m ${diff % 60}s`;
              })()}
            </span>
          )}
        </div>

        <div className="flex items-center gap-0.5 -mr-1">
          {job.status === "failed" && (
            <div className="relative group flex items-center justify-center">
              <button 
                onClick={handleRetry}
                disabled={isRetrying}
                className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-blue-500/10 text-muted-foreground hover:text-blue-500 transition-colors disabled:opacity-50"
              >
                <RotateCcw className={`h-3.5 w-3.5 ${isRetrying ? "animate-spin" : ""}`} />
              </button>
              <div className="absolute top-full mt-1.5 right-0 px-2 py-1 bg-foreground text-background font-medium text-[9px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                Retry Job
              </div>
            </div>
          )}

          {job.status === "completed" && job.audioUrl && (
            <div className="relative group flex items-center justify-center">
              <button className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-500 transition-colors">
                {downloadingFormat ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              </button>
              <div className="absolute top-full right-0 pt-1.5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none group-hover:pointer-events-auto z-50">
                <div className="bg-background border border-border shadow-md rounded-md flex flex-col min-w-[70px] overflow-hidden">
                  <button
                    onClick={() => handleDownloadClick("mp3")}
                    disabled={downloadingFormat !== null}
                    className="px-3 py-1.5 text-[10px] font-bold tracking-wider text-left hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                  >
                    MP3
                  </button>
                  <button
                    onClick={() => handleDownloadClick("m4a")}
                    disabled={downloadingFormat !== null}
                    className="px-3 py-1.5 text-[10px] font-bold tracking-wider text-left hover:bg-muted text-muted-foreground hover:text-foreground transition-colors border-t border-border/50 disabled:opacity-50"
                  >
                    M4A
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="relative group flex items-center justify-center">
            <button 
              onClick={() => setPreviewOpen(true)}
              className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-indigo-500/10 text-muted-foreground hover:text-indigo-500 transition-colors"
            >
              <Layers className="h-3.5 w-3.5" />
            </button>
            <div className="absolute top-full mt-1.5 right-0 px-2 py-1 bg-foreground text-background font-medium text-[9px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Preview Text
            </div>
          </div>
          
          <div className="relative group flex items-center justify-center">
            <button 
              onClick={() => onReparse?.(job.text, job.sourceFileName || undefined)}
              className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-orange-500/10 text-muted-foreground hover:text-orange-500 transition-colors"
            >
              <CornerUpLeft className="h-3.5 w-3.5" />
            </button>
            <div className="absolute top-full mt-1.5 right-0 px-2 py-1 bg-foreground text-background font-medium text-[9px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Load to Composer
            </div>
          </div>

          <div className="relative group flex items-center justify-center">
            <button 
              onClick={handleDelete}
              disabled={isDeleting}
              className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors disabled:opacity-50"
            >
              {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            </button>
            <div className="absolute top-full mt-1.5 right-0 px-2 py-1 bg-foreground text-background font-medium text-[9px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Delete Job
            </div>
          </div>
        </div>
      </div>

      {/* CONTENT: Text Preview */}
      <div className="bg-muted/40 rounded-lg p-2.5 border border-border/40 relative z-20">
        <p className={`text-xs leading-relaxed line-clamp-2 ${job.status === "completed" ? "text-foreground font-medium" : "text-muted-foreground"}`}>
          {job.textPreview}
        </p>
      </div>

      {/* FOOTER: Audio Player & Formats */}
      {job.status === "completed" && job.audioUrl && (
        <div className="flex items-center gap-2 pt-0.5 relative z-20">
          <div className="flex-1 flex items-center gap-1.5 rounded-lg bg-muted/40 border border-border/50 p-1 pl-1.5 pr-2.5 h-8 shadow-sm">
            <div className="flex items-center gap-0.5 flex-none">
              <button
                onPointerDown={() => startSeeking("rewind")}
                onPointerUp={stopSeeking}
                onPointerLeave={stopSeeking}
                onContextMenu={(e) => e.preventDefault()}
                className="flex items-center justify-center h-6 w-6 rounded-md bg-background shadow-sm hover:bg-muted text-muted-foreground transition-all select-none"
                title="Rewind 10s (Hold to seek continuously)"
              >
                <Rewind className="h-3 w-3" />
              </button>
              <button
                onClick={togglePlay}
                className={`flex items-center justify-center h-6 w-6 rounded-md transition-all ${
                  playing 
                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" 
                    : "bg-background shadow-sm hover:bg-primary/10 hover:text-primary text-muted-foreground"
                }`}
              >
                {playing ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3 ml-0.5" />}
              </button>
              <button
                onPointerDown={() => startSeeking("forward")}
                onPointerUp={stopSeeking}
                onPointerLeave={stopSeeking}
                onContextMenu={(e) => e.preventDefault()}
                className="flex items-center justify-center h-6 w-6 rounded-md bg-background shadow-sm hover:bg-muted text-muted-foreground transition-all select-none"
                title="Forward 10s (Hold to seek continuously)"
              >
                <FastForward className="h-3 w-3" />
              </button>
            </div>
            
            <div 
              ref={sliderRef}
              className="flex-1 h-2 bg-border/50 rounded-full overflow-hidden cursor-pointer relative group"
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
              title="Drag or scroll to seek"
            >
              <div 
                className="absolute top-0 left-0 h-full bg-primary transition-all duration-100 ease-linear"
                style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
              />
              {/* Hover indicator for easier dragging */}
              <div className="absolute top-0 left-0 w-full h-full opacity-0 group-hover:opacity-10 transition-opacity bg-primary" />
            </div>
            
            <div className="flex items-center gap-1 flex-none text-[9px] font-medium text-muted-foreground/80 tabular-nums">
              <span>{formatTime(currentTime)}</span>
              <span>/</span>
              <span className="text-primary/70">{formatTime(duration || job.audioDuration || 0)}</span>
            </div>
          </div>
        </div>
      )}

      <audio 
        ref={audioRef} 
        onEnded={() => setPlaying(false)} 
        onPause={() => setPlaying(false)}
        onPlay={() => setPlaying(true)}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        className="hidden" 
      />

      {job.status === "failed" && (
        <div className="mt-1 p-2 rounded-md bg-destructive/10 border border-destructive/20 relative z-20">
          <p className="text-[10px] font-medium text-destructive">
            {job.errorMessage || "An error occurred"}
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
