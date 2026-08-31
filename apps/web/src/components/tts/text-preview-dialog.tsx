import { useEffect, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import {
  X,
  FileText,
  Download,
  Copy,
  Check,
  Search,
  ArrowUpRight,
  Mic,
  Clock,
  Sparkles,
} from "lucide-react";
import { TTSJob } from "@/types/tts-job";
import { getFirstLine, slugify } from "@/lib/utils";
import { useTranslation } from "@/hooks/use-translation";
import { ALL_TAGS, findTagByToken } from "@/features/audio-studio/lib/delivery-tags";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

type TextPreviewDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  job: TTSJob | null;
  onReparse?: (jobText: string, fileName?: string) => void;
};

export function TextPreviewDialog({
  isOpen,
  onClose,
  job,
  onReparse,
}: TextPreviewDialogProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

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

  const rawText = job?.text || "";

  // Compute text statistics
  const stats = useMemo(() => {
    if (!rawText) {
      return {
        paragraphs: 0,
        words: 0,
        chars: 0,
        durationFormatted: "0s",
        totalCues: 0,
      };
    }

    const lines = rawText.split("\n").filter((line) => line.trim().length > 0);
    const words = rawText.trim().split(/\s+/).filter(Boolean).length;
    const chars = rawText.length;

    // Estimate duration based on ~150 words per minute at rate
    const rate = typeof job?.rate === "number" && job.rate > 0 ? job.rate : 1.0;
    const totalMinutes = words / (150 * rate);

    let durationFormatted = "";
    if (totalMinutes < 1) {
      durationFormatted = `${Math.max(5, Math.round(totalMinutes * 60))}s`;
    } else if (totalMinutes < 60) {
      durationFormatted = `${Math.round(totalMinutes)} phút`;
    } else {
      const hrs = Math.floor(totalMinutes / 60);
      const mins = Math.round(totalMinutes % 60);
      durationFormatted = mins > 0 ? `${hrs}h ${mins}p` : `${hrs} giờ`;
    }

    // Count recognized tags
    const tagMatches = rawText.match(/\[([^\]]+)\]/g) || [];
    let recognizedCues = 0;
    tagMatches.forEach((token) => {
      if (findTagByToken(token)) recognizedCues += 1;
    });

    return {
      paragraphs: lines.length || 1,
      words,
      chars,
      durationFormatted,
      totalCues: recognizedCues,
    };
  }, [rawText, job?.rate]);

  const handleCopyText = async () => {
    if (!rawText) return;
    try {
      await navigator.clipboard.writeText(rawText);
      setCopied(true);
      toast.success("Đã sao chép kịch bản vào bộ nhớ tạm");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Không thể sao chép văn bản");
    }
  };

  const handleDownloadText = () => {
    if (!job) return;
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

  const handleLoadToEditor = () => {
    if (!job || !onReparse) return;
    onReparse(job.text, job.sourceFileName || undefined);
    onClose();
    toast.success("Đã nạp kịch bản vào Editor!");
  };

  // Render paragraphs with line numbers and highlighted tags
  const renderedParagraphs = useMemo(() => {
    if (!rawText) return [];
    const paragraphs = rawText.split("\n");
    const q = searchQuery.trim().toLowerCase();

    return paragraphs.map((paragraph, pIdx) => {
      // Split paragraph by tags `[...]`
      const parts = paragraph.split(/(\[[^\]]+\])/g);

      return (
        <div
          key={pIdx}
          className="group/line flex items-start gap-3 sm:gap-4 py-1 hover:bg-muted/30 px-2 sm:px-3 rounded-xl transition-colors"
        >
          <span className="w-6 sm:w-7 shrink-0 text-right font-mono text-[11px] text-muted-foreground/30 select-none pt-1">
            {pIdx + 1}
          </span>
          <div className="flex-1 text-sm sm:text-base leading-relaxed text-foreground/90 font-normal break-words">
            {parts.map((part, idx) => {
              if (part.startsWith("[") && part.endsWith("]")) {
                const tag = findTagByToken(part);
                if (tag) {
                  const isNative = tag.type === "native";
                  const isEmotion = tag.type === "emotion";
                  return (
                    <span
                      key={idx}
                      className={cn(
                        "inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-lg text-xs font-bold border align-baseline select-none shadow-2xs",
                        isNative
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25"
                          : isEmotion
                            ? "bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/25"
                            : "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/25"
                      )}
                      title={`${tag.token} - ${tag.description || tag.label}`}
                    >
                      <span className="text-xs">{tag.icon}</span>
                      <span>{tag.label}</span>
                    </span>
                  );
                }
              }

              // Text highlight if searching
              if (q && part.toLowerCase().includes(q)) {
                const regex = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
                const splitQuery = part.split(regex);
                return (
                  <span key={idx}>
                    {splitQuery.map((sub, sIdx) =>
                      sub.toLowerCase() === q ? (
                        <mark
                          key={sIdx}
                          className="bg-amber-400/40 dark:bg-amber-500/30 text-foreground rounded px-0.5 font-bold"
                        >
                          {sub}
                        </mark>
                      ) : (
                        sub
                      )
                    )}
                  </span>
                );
              }

              return <span key={idx}>{part}</span>;
            })}
          </div>
        </div>
      );
    });
  }, [rawText, searchQuery]);

  if (!isOpen || !job || typeof document === "undefined") return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 dark:bg-black/80 backdrop-blur-md p-4 sm:p-6 overflow-hidden animate-backdrop-in"
      style={{
        animation: "modal-fade-in 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="w-full max-w-3xl h-[82vh] max-h-[calc(100dvh-3.5rem)] flex flex-col rounded-3xl border border-border/80 bg-card text-card-foreground shadow-2xl overflow-hidden animate-modal-in ring-1 ring-black/5 dark:ring-white/10 relative"
        style={{
          animation: "modal-scale-in 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Minimalist Header & Stats Bar */}
        <div className="shrink-0 border-b border-border/60 bg-muted/20 px-5 pt-5 pb-4 text-center space-y-2.5 relative">
          {/* Close button in top right */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
            title="Đóng (Esc)"
          >
            <X className="h-4 w-4" />
          </button>

          {/* Search Toggle button in top left */}
          <button
            onClick={() => setIsSearching((prev) => !prev)}
            className={cn(
              "absolute top-4 left-4 flex h-8 px-2.5 items-center gap-1.5 rounded-full text-xs font-semibold transition-colors cursor-pointer border",
              isSearching
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground border-border/50"
            )}
            title="Tìm kiếm từ khóa"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Tìm kiếm</span>
          </button>

          {/* Main Title */}
          <h3 className="text-lg sm:text-xl font-extrabold tracking-tight text-foreground">
            Kịch bản chi tiết
          </h3>

          {/* Voice Pill */}
          <div className="flex items-center justify-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 text-primary border border-primary/20 px-3 py-0.5 text-xs font-bold shadow-2xs">
              <Mic className="h-3 w-3" />
              <span>{job.voiceDisplayName || job.voiceType}</span>
              <span className="opacity-60">·</span>
              <span>{job.rate || 1.0}x</span>
            </span>
          </div>

          {/* Compact Stats Row */}
          <div className="flex items-center justify-center gap-2 sm:gap-3 text-xs font-medium text-muted-foreground flex-wrap">
            <span>{stats.paragraphs.toLocaleString()} đoạn</span>
            <span className="opacity-30">•</span>
            <span>{stats.chars.toLocaleString()} ký tự</span>
            <span className="opacity-30">•</span>
            <span className="flex items-center gap-1 font-semibold text-foreground">
              <Clock className="h-3 w-3 text-primary" />
              <span>{stats.durationFormatted}</span>
            </span>
            {stats.totalCues > 0 && (
              <>
                <span className="opacity-30">•</span>
                <span className="flex items-center gap-1 font-bold text-amber-600 dark:text-amber-400">
                  <Sparkles className="h-3 w-3" />
                  <span>{stats.totalCues} thẻ cảm xúc</span>
                </span>
              </>
            )}
          </div>

          {/* Collapsible Search Input */}
          {isSearching && (
            <div className="pt-2 max-w-md mx-auto relative animate-in fade-in zoom-in-95 duration-100">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Nhập từ khóa cần tìm trong kịch bản..."
                autoFocus
                className="h-8 w-full rounded-full border border-border/80 bg-background pl-8 pr-8 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none shadow-xs"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Reader Document Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-8 py-5 custom-scrollbar bg-background/50">
          <div className="max-w-2xl mx-auto space-y-1 pb-20">
            {renderedParagraphs}
          </div>
        </div>

        {/* Floating Minimalist Action Pill Bar at Bottom */}
        <div
          className="absolute bottom-4 left-1/2 z-30 animate-pill-in"
          style={{
            animation: "modal-pill-in 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
          }}
        >
          <div className="flex items-center gap-1.5 rounded-full border border-border/80 bg-background/95 p-1.5 shadow-2xl backdrop-blur-xl ring-1 ring-black/10 dark:ring-white/10">
            {onReparse && (
              <button
                type="button"
                onClick={handleLoadToEditor}
                className="inline-flex items-center gap-1.5 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-1.5 text-xs font-bold shadow-xs transition-all cursor-pointer hover:scale-105 active:scale-95"
              >
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>Nạp vào Editor</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleCopyText}
              className="inline-flex items-center gap-1.5 rounded-full hover:bg-muted text-foreground px-3.5 py-1.5 text-xs font-semibold transition-colors cursor-pointer"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5 text-muted-foreground" />}
              <span>{copied ? "Đã chép" : "Sao chép"}</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadText}
              className="inline-flex items-center gap-1.5 rounded-full hover:bg-muted text-foreground px-3.5 py-1.5 text-xs font-semibold transition-colors cursor-pointer"
            >
              <Download className="h-3.5 w-3.5 text-muted-foreground" />
              <span>Tải TXT</span>
            </button>

            <div className="w-px h-3.5 bg-border/60 mx-0.5" />

            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center rounded-full hover:bg-muted text-muted-foreground hover:text-foreground px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
