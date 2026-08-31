import React, { useState } from "react";
import {
  Sparkles,
  Loader2,
  Mic,
  Play,
  Pause,
  ExternalLink,
  ChevronDown,
  FileText,
  Gauge,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/hooks/use-translation";
import { cn } from "@/lib/utils";
import type { CustomVoice } from "@/types/voice";
import type { TTSJob } from "@/types/tts-job";

interface VoiceLabFloatingBarProps {
  profile: CustomVoice | null | undefined;
  previewText: string;
  setPreviewText: (text: string) => void;
  previewRate: string;
  setPreviewRate: (rate: string) => void;
  referenceTranscript?: string;
  previewJob: TTSJob | null | undefined;
  previewJobError: boolean;
  isLoadingPreviewAudio: boolean;
  previewAudioBlobUrl: string | null;
  isPreviewPlaying: boolean;
  previewDuration: number;
  previewCurrentTime: number;
  togglePlayPreview: () => void;
  handlePreviewSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
  generatePreview: () => Promise<void> | void;
  downloadingFormat: "wav" | "mp3" | "m4a" | null;
  handleDownloadPreview: (format: "wav" | "mp3" | "m4a") => void;
}

export function VoiceLabFloatingBar({
  profile,
  previewText,
  setPreviewText,
  previewRate,
  setPreviewRate,
  referenceTranscript,
  previewJob,
  previewJobError,
  isLoadingPreviewAudio,
  previewAudioBlobUrl,
  isPreviewPlaying,
  previewDuration,
  previewCurrentTime,
  togglePlayPreview,
  handlePreviewSeek,
  generatePreview,
  downloadingFormat,
  handleDownloadPreview,
}: VoiceLabFloatingBarProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  const isGenerating =
    previewJob?.status === "queued" || previewJob?.status === "processing";

  const ratePresets = [
    { label: "0.75×", value: "0.75" },
    { label: "1.0× (Chuẩn)", value: "1" },
    { label: "1.25×", value: "1.25" },
    { label: "1.5×", value: "1.5" },
    { label: "2.0×", value: "2" },
  ];

  const rateLabels: Record<string, string> = {
    "0.75": "0.75×",
    "1": "1.0×",
    "1.25": "1.25×",
    "1.5": "1.5×",
    "2": "2.0×",
  };

  const previewSnippets = [
    {
      label: "👋 Lời chào",
      text: "Xin chào các bạn, hôm nay tôi sẽ hướng dẫn các bạn cách ứng dụng trí tuệ nhân tạo để làm việc hiệu quả hơn.",
    },
    {
      label: "📖 Kể chuyện",
      text: "Đêm ấy, ánh trăng chiếu rọi xuống mặt hồ phẳng lặng như gương. Gió thu se lạnh khẽ lướt qua rặng liễu ven bờ.",
    },
    {
      label: "📰 Tin tức",
      text: "Bản tin công nghệ: Mô hình giọng nói AI cục bộ đang thay đổi hoàn toàn quy trình sáng tạo âm thanh và lồng tiếng video.",
    },
  ];

  return (
    <aside
      aria-label="Voice Lab Action Bar"
      className="sticky bottom-3 sm:bottom-4 z-40 w-full animate-in fade-in slide-in-from-bottom-3 duration-300 pointer-events-auto"
    >
      <div className="rounded-2xl sm:rounded-3xl border border-border/80 bg-card/95 dark:bg-card/95 p-3 sm:p-3.5 shadow-2xl backdrop-blur-xl ring-1 ring-black/5 dark:ring-white/10 transition-all duration-300 space-y-0">
        {/* Full Clickable Header Summary Bar */}
        <div
          onClick={() => setIsExpanded((prev) => !prev)}
          className="flex flex-wrap items-center justify-between gap-2.5 sm:gap-3.5 cursor-pointer select-none group/bar"
          title={isExpanded ? "Bấm để thu gọn kịch bản" : "Bấm để mở rộng chỉnh kịch bản & tạo nghe thử"}
        >
          {/* Left Section: Voice Profile Pill & Mini Player */}
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-wrap">
            {/* Profile Pill */}
            <div className="flex items-center gap-2 rounded-xl bg-muted/60 px-3 py-1.5 sm:py-2 border border-border/50 max-w-[180px] sm:max-w-[220px]">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Mic className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1 truncate">
                <p className="truncate text-xs font-bold text-foreground">
                  {profile?.display_name || t("voiceLab.voiceNotSelected")}
                </p>
                <p className="truncate text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                  {profile ? "VieNeu Clone" : "Phòng thu AI"}
                </p>
              </div>
            </div>

            {/* Mini Player when preview audio is available */}
            {previewJob?.status === "completed" && previewAudioBlobUrl && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-2 rounded-xl bg-primary/5 dark:bg-primary/10 border border-primary/20 px-2.5 py-1 sm:py-1.5 shadow-2xs cursor-default"
              >
                <button
                  type="button"
                  onClick={togglePlayPreview}
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-xs hover:bg-primary/90 transition-all active:scale-95 cursor-pointer"
                  title={isPreviewPlaying ? "Tạm dừng" : "Phát bản nghe thử"}
                >
                  {isPreviewPlaying ? (
                    <Pause className="h-3.5 w-3.5 fill-current" />
                  ) : (
                    <Play className="h-3.5 w-3.5 fill-current ml-0.5" />
                  )}
                </button>

                <div className="flex flex-col gap-0.5 min-w-[75px] sm:min-w-[100px]">
                  <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
                    <span className="font-bold text-foreground">{previewCurrentTime.toFixed(1)}s</span>
                    <span>{previewDuration > 0 ? `${previewDuration.toFixed(1)}s` : "—"}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={previewDuration || 100}
                    step={0.1}
                    value={previewCurrentTime}
                    onChange={handlePreviewSeek}
                    disabled={previewDuration <= 0}
                    className="h-1 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary disabled:cursor-not-allowed"
                  />
                </div>

                {/* Quick Downloads */}
                <div className="hidden sm:flex items-center gap-1 pl-1 border-l border-border/50">
                  <button
                    type="button"
                    onClick={() => handleDownloadPreview("wav")}
                    disabled={downloadingFormat !== null}
                    className="rounded-md border border-border/60 bg-background/80 px-2 py-1 text-[10px] font-bold hover:bg-primary/10 hover:text-primary transition-all disabled:opacity-50 cursor-pointer shadow-2xs"
                    title="Tải file WAV 24kHz"
                  >
                    {downloadingFormat === "wav" ? <Loader2 className="h-3 w-3 animate-spin" /> : "WAV"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownloadPreview("mp3")}
                    disabled={downloadingFormat !== null}
                    className="rounded-md border border-border/60 bg-background/80 px-2 py-1 text-[10px] font-bold hover:bg-primary/10 hover:text-primary transition-all disabled:opacity-50 cursor-pointer shadow-2xs"
                    title="Tải file MP3"
                  >
                    {downloadingFormat === "mp3" ? <Loader2 className="h-3 w-3 animate-spin" /> : "MP3"}
                  </button>
                </div>
              </div>
            )}

            {/* Generating Status Badge */}
            {isGenerating && (
              <div className="flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3 py-1.5 text-xs font-bold text-primary animate-pulse">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Đang tổng hợp...</span>
              </div>
            )}
          </div>

          {/* Center: Script preview snippet (Visible ONLY when collapsed) */}
          {!isExpanded && (
            <div className="hidden md:flex items-center gap-2 min-w-0 max-w-[260px] truncate rounded-xl border border-border/60 bg-background/60 group-hover/bar:bg-muted/60 px-3 py-1.5 text-xs transition-all">
              <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
              <span className="truncate text-foreground/80 font-medium">
                {previewText.trim() ? previewText : t("voiceLab.compactSnippetPlaceholder")}
              </span>
              <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-mono font-bold text-muted-foreground shrink-0">
                {rateLabels[previewRate] || `${previewRate}x`}
              </span>
            </div>
          )}

          {/* Right Section: Toggle Button & Link to Studio */}
          <div className="flex items-center gap-2 min-w-0 shrink-0">
            {/* Open in Studio Link (if profile available) */}
            {profile && (
              <a
                href={`/generate?voice=${profile.id}`}
                onClick={(e) => e.stopPropagation()}
                className="hidden lg:inline-flex items-center gap-1 rounded-xl border border-border/60 bg-muted/40 hover:bg-muted px-3 py-2 text-xs font-semibold text-foreground transition-colors cursor-pointer"
                title="Mở giọng đọc này trong Audio Studio"
              >
                <span>Vào Studio</span>
                <ExternalLink className="h-3 w-3 text-muted-foreground" />
              </a>
            )}

            {/* Expand / Collapse Toggle Button */}
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-xl border border-border/60 bg-muted/40 group-hover/bar:bg-muted/80 px-3 py-1.5 sm:py-2 text-xs font-semibold text-foreground transition-all shadow-2xs",
                isExpanded && "bg-primary/10 border-primary/30 text-primary font-bold"
              )}
            >
              <span>{isExpanded ? t("voiceLab.collapseScript") : t("voiceLab.expandScript")}</span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform duration-300 text-muted-foreground group-hover/bar:text-foreground",
                  isExpanded && "rotate-180 text-primary"
                )}
              />
            </div>
          </div>
        </div>

        {/* Expandable Area: Full Studio Integration UI */}
        <div
          className={cn(
            "grid transition-all duration-300 ease-out",
            isExpanded
              ? "grid-rows-[1fr] opacity-100 mt-3 pt-3 border-t border-border/60"
              : "grid-rows-[0fr] opacity-0 mt-0 pt-0 border-t-0 pointer-events-none"
          )}
        >
          <div className="overflow-hidden space-y-3.5 pt-1">
            {/* Header description */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    {t("voiceLab.useInStudio", "Sử dụng trong Studio")}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Thử nghiệm tạo giọng đọc AI từ văn bản tùy ý hoặc chuyển tiếp trực tiếp vào Studio
                  </p>
                </div>
              </div>

              {profile && (
                <a
                  href={`/generate?voice=${profile.id}`}
                  className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-xl border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-bold text-primary hover:bg-primary/10 transition-colors cursor-pointer"
                >
                  <span>Mở trong Studio</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>

            {/* Quick Sample Template Chips */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
                <FileText className="h-3.5 w-3.5" /> Mẫu nhanh:
              </span>
              {referenceTranscript && referenceTranscript.trim() && (
                <button
                  type="button"
                  onClick={() => setPreviewText(referenceTranscript.trim())}
                  disabled={!profile}
                  className="rounded-lg border border-border/80 bg-background/80 px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
                >
                  🎙️ Lời thoại gốc
                </button>
              )}
              {previewSnippets.map((snippet, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPreviewText(snippet.text)}
                  disabled={!profile}
                  className="rounded-lg border border-border/80 bg-background/80 px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
                >
                  {snippet.label}
                </button>
              ))}
            </div>

            {/* Full Textarea Container */}
            <div className="relative rounded-2xl border border-border bg-background transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 shadow-2xs">
              <textarea
                value={previewText}
                onChange={(event) => setPreviewText(event.target.value)}
                disabled={!profile}
                maxLength={500}
                placeholder={
                  profile
                    ? t("voiceLab.previewTextPlaceholder", "Nhập nội dung bạn muốn giọng đọc thử nghiệm...")
                    : t("voiceLab.createProfileToUnlockDesc", "Tạo hồ sơ giọng để mở khóa tính năng nghe thử và tạo âm thanh.")
                }
                rows={3}
                className="w-full resize-y bg-transparent p-3.5 text-xs sm:text-sm outline-none placeholder:text-muted-foreground/60 disabled:cursor-not-allowed leading-relaxed"
              />
              <div className="flex items-center justify-between border-t border-border/50 bg-muted/20 px-3.5 py-1.5 text-[11px] text-muted-foreground">
                <span>Nhập tối đa 500 ký tự cho bản nghe thử</span>
                <span className="font-mono">{previewText.length}/500</span>
              </div>
            </div>

            {/* Expanded Bottom Controls: Speed Selector & Primary Action Button */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
              {/* Speed Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1 shrink-0">
                  <Gauge className="h-3.5 w-3.5 text-primary" />
                  {t("generate.speed", "Tốc độ")}:
                </span>
                <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 p-1 flex-wrap">
                  {ratePresets.map((preset) => {
                    const isSelected = previewRate === preset.value;
                    return (
                      <button
                        key={preset.value}
                        type="button"
                        onClick={() => setPreviewRate(preset.value)}
                        disabled={!profile}
                        className={cn(
                          "rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
                          isSelected
                            ? "bg-primary text-primary-foreground shadow-xs font-bold"
                            : "text-muted-foreground hover:text-foreground hover:bg-background/60"
                        )}
                      >
                        {preset.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Primary Action Button: Generate Preview (Shown inside expanded content) */}
              <Button
                type="button"
                onClick={() => void generatePreview()}
                disabled={!profile || !previewText.trim() || isGenerating}
                className="rounded-xl sm:rounded-2xl bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-xs sm:text-sm px-5 py-2.5 gap-2 shadow-sm transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer shrink-0 self-end sm:self-auto disabled:opacity-40"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>{t("voiceLab.synthesizing", "Đang tạo...")}</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    <span>{t("voiceLab.generatePreview", "Tạo bản nghe thử")}</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
