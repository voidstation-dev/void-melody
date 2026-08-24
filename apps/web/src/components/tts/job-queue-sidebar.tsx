import { useQueue } from "@/hooks/use-queue";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  Pause,
  Trash2,
  RotateCcw,
  Layers,
  CornerUpLeft,
  RefreshCw,
  Rewind,
  FastForward,
  Download,
  ChevronDown,
  ChevronUp,
  Volume2,
  Activity,
  Sparkles,
  Copy,
  Check,
  Filter,
} from "lucide-react";
import { TTSJob } from "@/types/tts-job";
import { apiFetchBlob } from "@/lib/api-client";
import { useEffect, useState, useRef, useMemo } from "react";
import { AudioDownloadDialog } from "./audio-download-dialog";
import { TextPreviewDialog } from "./text-preview-dialog";
import { useTranslation } from "@/hooks/use-translation";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

type FilterTab = "all" | "active" | "completed" | "failed";

export interface JobQueueSidebarProps {
  onReparse?: (jobText: string, fileName?: string) => void;
  className?: string;
  maxHeightClass?: string;
  title?: string;
}

export function JobQueueSidebar({
  onReparse,
  className,
  maxHeightClass = "max-h-[380px] sm:max-h-[440px]",
  title,
}: JobQueueSidebarProps) {
  const { queue, activeJobs, refreshQueue, removeFromQueue } = useQueue();
  const { t } = useTranslation();
  const [filter, setFilter] = useState<FilterTab>("all");
  const [isClearingCompleted, setIsClearingCompleted] = useState(false);

  // Categorize counts
  const completedJobs = useMemo(() => queue.filter((j) => j.status === "completed"), [queue]);
  const failedJobs = useMemo(() => queue.filter((j) => j.status === "failed"), [queue]);

  // Filter and sort queue
  const filteredQueue = useMemo(() => {
    let list = queue;
    if (filter === "active") {
      list = queue.filter((j) => j.status === "processing" || j.status === "queued");
    } else if (filter === "completed") {
      list = completedJobs;
    } else if (filter === "failed") {
      list = failedJobs;
    }

    return [...list].sort((a, b) => {
      const aActive = a.status === "processing" || a.status === "queued" ? 1 : 0;
      const bActive = b.status === "processing" || b.status === "queued" ? 1 : 0;
      if (aActive !== bActive) return bActive - aActive;

      if (a.batchId && b.batchId && a.batchId === b.batchId) {
        return (a.batchPosition ?? 0) - (b.batchPosition ?? 0);
      }

      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
  }, [queue, filter, completedJobs, failedJobs]);

  const handleClearCompleted = async () => {
    if (completedJobs.length === 0 || isClearingCompleted) return;
    setIsClearingCompleted(true);
    try {
      await Promise.all(completedJobs.map((j) => removeFromQueue(j.id)));
      toast.success(`Đã xóa ${completedJobs.length} tác vụ đã hoàn thành`);
    } catch {
      toast.error("Không thể xóa tác vụ đã hoàn thành");
    } finally {
      setIsClearingCompleted(false);
    }
  };

  if (queue.length === 0) {
    return (
      <Card className={cn("rounded-2xl border-2 border-dashed border-border/70 bg-card/60 p-6 flex flex-col items-center justify-center text-center overflow-hidden min-h-[180px] group transition-all hover:border-primary/40 shadow-xs", className)}>
        <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-muted/80 shadow-xs border border-border/50 mb-3 group-hover:scale-110 group-hover:bg-primary/10 transition-all duration-300">
          <Layers className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
        <h3 className="text-xs font-bold text-foreground mb-1">{t("generate.queueEmpty")}</h3>
        <p className="text-[11px] text-muted-foreground max-w-[220px] leading-normal">
          {t("generate.queueEmptyDesc")}
        </p>
      </Card>
    );
  }

  return (
    <Card className={cn("rounded-2xl border border-border/80 bg-card shadow-sm overflow-hidden flex flex-col", className)}>
      {/* Header with Title & Stats */}
      <CardHeader className="p-3.5 pb-2.5 border-b border-border/60 bg-muted/20 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
              <Activity className="h-3.5 w-3.5" />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-foreground flex items-center gap-1.5">
                <span>{title || t("generate.queueTitle")}</span>
                <span className="text-[10px] font-mono font-bold text-muted-foreground">({queue.length})</span>
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {activeJobs.length > 0 && (
              <Badge variant="outline" className="h-5 px-1.5 text-[10px] font-bold bg-primary/10 text-primary border-primary/30 animate-pulse">
                <Loader2 className="h-2.5 w-2.5 animate-spin mr-1" />
                {activeJobs.length} {t("generate.statusProcessing")}
              </Badge>
            )}

            <button
              onClick={() => refreshQueue()}
              className="flex items-center justify-center h-6 w-6 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              title={t("generate.refreshTooltip")}
            >
              <RefreshCw className="h-3 w-3" />
            </button>

            {completedJobs.length > 0 && (
              <button
                onClick={handleClearCompleted}
                disabled={isClearingCompleted}
                className="flex items-center gap-1 h-6 px-1.5 text-[10px] font-semibold rounded-md hover:bg-muted text-muted-foreground hover:text-rose-500 transition-colors disabled:opacity-50"
                title={t("jobQueue.clearCompleted")}
              >
                <Trash2 className="h-3 w-3" />
                <span className="hidden sm:inline">{t("jobQueue.clearCompleted")}</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 pt-0.5 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-0.5 rounded-lg text-[10px] font-bold transition-colors whitespace-nowrap",
              filter === "all"
                ? "bg-primary text-primary-foreground shadow-2xs"
                : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {t("generate.tabAll")} ({queue.length})
          </button>
          <button
            onClick={() => setFilter("active")}
            className={cn(
              "px-2 py-0.5 rounded-lg text-[10px] font-bold transition-colors whitespace-nowrap flex items-center gap-1",
              filter === "active"
                ? "bg-primary text-primary-foreground shadow-2xs"
                : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {t("generate.tabProcessing")} ({activeJobs.length})
          </button>
          <button
            onClick={() => setFilter("completed")}
            className={cn(
              "px-2 py-0.5 rounded-lg text-[10px] font-bold transition-colors whitespace-nowrap",
              filter === "completed"
                ? "bg-primary text-primary-foreground shadow-2xs"
                : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {t("generate.tabCompleted")} ({completedJobs.length})
          </button>
          {failedJobs.length > 0 && (
            <button
              onClick={() => setFilter("failed")}
              className={cn(
                "px-2 py-0.5 rounded-lg text-[10px] font-bold transition-colors whitespace-nowrap text-rose-600 dark:text-rose-400",
                filter === "failed"
                  ? "bg-rose-500 text-white shadow-2xs"
                  : "bg-rose-500/10 hover:bg-rose-500/20",
              )}
            >
              {t("generate.tabFailed")} ({failedJobs.length})
            </button>
          )}
        </div>
      </CardHeader>

      {/* Bounded Scrollable Queue List */}
      <CardContent className={cn("p-3.5 pt-4 sm:p-4 sm:pt-5 overflow-y-auto space-y-3 pr-1.5 divide-y-0", maxHeightClass)}>
        {filteredQueue.length === 0 ? (
          <div className="py-6 text-center text-xs text-muted-foreground flex flex-col items-center gap-1">
            <Filter className="h-4 w-4 opacity-40 mb-0.5" />
            <span>{t("jobQueue.emptyFilter")}</span>
          </div>
        ) : (
          filteredQueue.map((job) => (
            <JobItem key={job.id} job={job} onReparse={onReparse} />
          ))
        )}
      </CardContent>
    </Card>
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
  const [isExpanded, setIsExpanded] = useState(job.status === "processing");
  const [copiedText, setCopiedText] = useState(false);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState<"mp3" | "m4a" | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<"mp3" | "m4a" | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobUrlRef = useRef<string | null>(null);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const sliderRef = useRef<HTMLDivElement>(null);
  const seekIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isUUID = (str?: string | null) =>
    Boolean(str && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str));

  const isCustomVoice = Boolean(
    job.voiceType &&
      (job.voiceType.startsWith("custom_") || isUUID(job.voiceType))
  );
  const isVieneuPreset = !isCustomVoice && job.providerId === "vieneu";
  const speedText = typeof job.rate === "number" ? `${job.rate}x` : "1.0x";

  // Auto-expand when active or starts playing
  useEffect(() => {
    if (job.status === "processing" || playing) {
      setIsExpanded(true);
    }
  }, [job.status, playing]);

  useEffect(() => {
    return () => {
      if (audioBlobUrlRef.current && typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(audioBlobUrlRef.current);
      }
    };
  }, [job.audioUrl]);

  const stopSeeking = () => {
    if (seekTimeoutRef.current) clearTimeout(seekTimeoutRef.current);
    if (seekIntervalRef.current) clearInterval(seekIntervalRef.current);
  };

  const startSeeking = (direction: "forward" | "rewind") => {
    if (!audioRef.current || !duration) return;
    const jump = direction === "forward" ? 10 : -10;
    const newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + jump));
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);

    seekTimeoutRef.current = setTimeout(() => {
      seekIntervalRef.current = setInterval(() => {
        if (!audioRef.current || !duration) return;
        const step = direction === "forward" ? 2 : -2;
        const t = Math.max(0, Math.min(duration, audioRef.current.currentTime + step));
        audioRef.current.currentTime = t;
        setCurrentTime(t);
      }, 100);
    }, 400);
  };

  const formatTime = (time: number) => {
    if (isNaN(time)) return "0:00";
    const m = Math.floor(time / 60);
    const s = Math.floor(time % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

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
        toast.error("Không thể nạp file âm thanh");
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
      toast.success(`Đã tải file ${format.toUpperCase()} thành công`);
    } catch (err) {
      console.error("Failed to download audio", err);
      toast.error("Không thể tải file audio");
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

  const handleCopyText = () => {
    if (!job.text) return;
    navigator.clipboard.writeText(job.text);
    setCopiedText(true);
    toast.success(t("jobQueue.copiedText"));
    setTimeout(() => setCopiedText(false), 2000);
  };

  return (
    <div
      className={cn(
        "group relative rounded-xl border transition-all duration-200 overflow-hidden",
        job.status === "processing"
          ? "border-primary/50 bg-primary/5 shadow-sm ring-1 ring-primary/20"
          : job.status === "failed"
            ? "border-destructive/30 bg-destructive/5 hover:border-destructive/50"
            : "border-border/60 bg-card hover:border-border hover:shadow-xs",
      )}
    >
      {/* Primary Row: Left Play/Status | Center Title & Snippet | Right Time & Actions */}
      <div className="flex items-center gap-2.5 p-2.5 sm:p-3 relative z-10">
        {/* Left Status Icon or Play Trigger */}
        <div className="shrink-0">
          {job.status === "completed" && job.audioUrl ? (
            <button
              onClick={togglePlay}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-xl transition-all shadow-2xs",
                playing
                  ? "bg-primary text-primary-foreground ring-2 ring-primary/30 scale-105"
                  : "bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground hover:scale-105 active:scale-95",
              )}
              title={playing ? t("generate.pauseTooltip") : t("generate.playTooltip")}
            >
              {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 ml-0.5" />}
            </button>
          ) : job.status === "processing" ? (
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          ) : job.status === "queued" ? (
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <Clock className="h-4 w-4 animate-pulse" />
            </div>
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-destructive/10 text-destructive border border-destructive/20">
              <XCircle className="h-4 w-4" />
            </div>
          )}
        </div>

        {/* Center: Voice Name + Speed + 1-Line Preview */}
        <div className="min-w-0 flex-1 cursor-pointer" onClick={() => setIsExpanded((prev) => !prev)}>
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-bold text-foreground truncate max-w-[130px] sm:max-w-[180px]">
              {job.voiceDisplayName || job.voiceType}
            </span>
            {isCustomVoice ? (
              <span className="shrink-0 rounded-md bg-violet-500/15 px-1 py-0.2 text-[9px] font-black uppercase text-violet-600 dark:text-violet-400">
                Clone
              </span>
            ) : isVieneuPreset ? (
              <span className="shrink-0 rounded-md bg-emerald-500/15 px-1 py-0.2 text-[9px] font-black uppercase text-emerald-600 dark:text-emerald-400">
                VieNeu
              </span>
            ) : null}
            <span
              className="shrink-0 rounded-md bg-muted/80 px-1.5 py-0.2 text-[9px] font-mono font-bold text-muted-foreground border border-border/50"
              title={t("jobQueue.speedTooltip")}
            >
              {speedText}
            </span>
            {job.status === "processing" && (
              <span className="text-[10px] font-bold text-primary font-mono">
                {job.progress && job.progress > 0 ? `${Math.round(job.progress)}%` : t("jobQueue.statusGenerating")}
              </span>
            )}
            {job.status === "queued" && (
              <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400">
                {t("jobQueue.statusWaiting")}
              </span>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground truncate leading-normal mt-0.5">
            {job.textPreview || job.text}
          </p>
        </div>

        {/* Right: Duration / Timestamp & Quick Action Buttons */}
        <div className="flex items-center gap-1 shrink-0">
          {job.status === "completed" && (
            <span className="text-[10px] font-mono font-bold text-muted-foreground/80 bg-muted/50 px-1.5 py-0.5 rounded-md hidden sm:inline-block">
              {formatTime(job.audioDuration || 0)}
            </span>
          )}

          {/* Quick Actions */}
          {job.status === "completed" && job.audioUrl && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer"
                  title={t("generate.downloadAudioTooltip")}
                >
                  {downloadingFormat ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-[120px] p-1 rounded-xl shadow-xl z-50">
                <DropdownMenuItem
                  onClick={() => handleDownloadClick("mp3")}
                  disabled={downloadingFormat !== null}
                  className="flex items-center justify-between gap-2 px-2.5 py-1.5 text-xs font-semibold cursor-pointer rounded-lg"
                >
                  <span className="font-bold">MP3</span>
                  <span className="text-[10px] font-medium text-muted-foreground">{t("jobQueue.audioLabel")}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => handleDownloadClick("m4a")}
                  disabled={downloadingFormat !== null}
                  className="flex items-center justify-between gap-2 px-2.5 py-1.5 text-xs font-semibold cursor-pointer rounded-lg"
                >
                  <span className="font-bold">M4A</span>
                  <span className="text-[10px] font-medium text-muted-foreground">{t("jobQueue.aacLabel")}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {job.status === "failed" && (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              title={t("generate.retryJobTooltip")}
            >
              <RotateCcw className={cn("h-3.5 w-3.5", isRetrying && "animate-spin")} />
            </button>
          )}

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
            className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-500 transition-colors disabled:opacity-50"
            title={t("generate.deleteJobTooltip")}
          >
            {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
          </button>

          {/* Expand/Collapse Toggle */}
          <button
            onClick={() => setIsExpanded((prev) => !prev)}
            className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title={isExpanded ? "Thu gọn" : "Mở rộng"}
          >
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Expandable Area: Progress Bar or Full Waveform & Text */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-border/40 space-y-2.5 animate-in fade-in duration-150">
          {/* Detailed Text Content */}
          <div className="relative rounded-lg bg-muted/40 p-2.5 border border-border/40 group/text">
            <p className="text-[11px] leading-relaxed text-foreground/90 max-h-24 overflow-y-auto pr-6 font-sans">
              {job.text}
            </p>
            <button
              onClick={handleCopyText}
              className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-md bg-background/80 hover:bg-background text-muted-foreground hover:text-foreground border border-border/50 transition-colors opacity-0 group-hover/text:opacity-100"
              title="Sao chép văn bản"
            >
              {copiedText ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
            </button>
          </div>

          {/* Full Interactive Waveform Player for completed jobs */}
          {job.status === "completed" && job.audioUrl && (
            <div className="flex items-center gap-2 rounded-xl bg-muted/50 border border-border/50 p-2 shadow-2xs">
              {/* Seeking controls */}
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onPointerDown={() => startSeeking("rewind")}
                  onPointerUp={stopSeeking}
                  onPointerLeave={stopSeeking}
                  className="flex items-center justify-center h-6 w-6 rounded-lg bg-background border border-border/40 hover:bg-muted text-muted-foreground hover:text-foreground transition-all select-none"
                  title={t("generate.rewindTooltip")}
                >
                  <Rewind className="h-3 w-3" />
                </button>

                <button
                  onClick={togglePlay}
                  className={cn(
                    "flex items-center justify-center h-7 w-7 rounded-lg transition-all shadow-xs",
                    playing
                      ? "bg-primary text-primary-foreground ring-2 ring-primary/20"
                      : "bg-primary text-primary-foreground hover:opacity-90 active:scale-95",
                  )}
                  title={playing ? t("generate.pauseTooltip") : t("generate.playTooltip")}
                >
                  {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 ml-0.5" />}
                </button>

                <button
                  onPointerDown={() => startSeeking("forward")}
                  onPointerUp={stopSeeking}
                  onPointerLeave={stopSeeking}
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

              {/* Time Indicators */}
              <div className="flex items-center gap-1 shrink-0 text-[10px] font-mono font-semibold text-muted-foreground tabular-nums">
                <span className="text-foreground">{formatTime(currentTime)}</span>
                <span className="text-muted-foreground/60">/</span>
                <span>{formatTime(duration || job.audioDuration || 0)}</span>
              </div>
            </div>
          )}

          {/* Failure Error Trace */}
          {job.status === "failed" && (
            <div className="p-2.5 rounded-lg bg-destructive/10 border border-destructive/20">
              <p className="text-[11px] leading-relaxed font-medium text-destructive break-words whitespace-pre-wrap max-h-24 overflow-y-auto">
                {job.errorMessage || t("errors.generic")}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Hidden Native Audio Element */}
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

      <TextPreviewDialog isOpen={previewOpen} onClose={() => setPreviewOpen(false)} job={job} />

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

