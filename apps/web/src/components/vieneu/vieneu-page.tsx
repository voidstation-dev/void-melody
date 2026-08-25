
import {
  ChangeEvent,
  DragEvent,
  SyntheticEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Check,
  Download,
  ExternalLink,
  FileAudio,
  FileText,
  Gauge,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Upload,
  UserRoundPlus,
  Volume2,
} from "lucide-react";
import { useVoiceCapabilities } from "@/hooks/use-voice-capabilities";
import { useTTSJob } from "@/hooks/use-tts-job";
import { useCustomVoice } from "@/hooks/use-custom-voice";
import { useVoiceLabStore } from "@/stores/voice-lab-store";
import { useSpeechModelsStore } from "@/stores/speech-models-store";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchBlob } from "@/lib/api-client";
import { BatchJobCreateResponse } from "@/types/tts-job";
import { useTranslation } from "@/hooks/use-translation";
import { toast } from "sonner";
import {
  DEFAULT_WAVEFORM_PEAKS,
} from "@/constants";

import { getVoiceCalibrationAudioUrl } from "@/lib/voice-lab-api";

function formatBytes(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function RuntimeBadge({
  isLoading,
  available,
  reason,
}: {
  isLoading: boolean;
  available: boolean;
  reason?: string | null;
}) {
  const { t } = useTranslation();
  if (isLoading)
    return (
      <span className="rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground">
        {t("voiceLab.runtimeChecking")}
      </span>
    );
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold ${available ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400" : "border-amber-200 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"}`}
      title={reason ?? undefined}
    >
      <span
        className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${available ? "bg-emerald-500" : "bg-amber-500"}`}
      />
      {available ? t("voiceLab.cloneReady") : t("voiceLab.cloneUnavailable")}
    </span>
  );
}

function StepCard({
  step,
  title,
  children,
}: {
  step: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
          {step}
        </span>
        <h2 className="text-base font-bold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Waveform({ peaks = [] }: { peaks?: number[] }) {
  const bars = peaks.length ? peaks : DEFAULT_WAVEFORM_PEAKS;
  return (
    <div
      className="flex h-24 items-center gap-1 rounded-xl border border-dashed border-border bg-muted/40 p-3"
      aria-label="Audio waveform preview"
    >
      {bars.map((height, index) => (
        <span
          key={index}
          className="w-full rounded-full bg-muted-foreground/25"
          style={{ height: `${height}%` }}
        />
      ))}
    </div>
  );
}

export function VieneuPage({
  initialVoiceId = null,
}: { initialVoiceId?: string | null } = {}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    file,
    fileUrl,
    fileError,
    voiceName,
    consent,
    selectedSegment,
    denoiseMode,
    cloneMode,
    referenceTranscript,
    transcriptSegmentKey,
    transcriptNeedsReview,
    analysis,
    isAnalyzing,
    analysisError,
    isCloning,
    cloneProgress,
    cloneStage,
    cloneError,
    createdProfile,
    previewText,
    previewRate,
    previewJobId,
    previewError,
    selectFile,
    setVoiceName,
    setConsent,
    setSelectedSegment,
    setDenoiseMode,
    setCloneMode,
    setReferenceTranscript,
    setTranscriptSegmentKey,
    setTranscriptNeedsReview,
    setPreviewText,
    setPreviewRate,
    setPreviewJobId,
    setPreviewError,
    startClone,
    reset,
  } = useVoiceLabStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const sourceAudioRef = useRef<HTMLAudioElement>(null);
  const capabilities = useVoiceCapabilities();
  const runtime = capabilities.data;
  const selectedProfile = useCustomVoice(initialVoiceId);
  const profile = createdProfile ?? selectedProfile.data;
  const { data: previewJob, isError: previewJobError } = useTTSJob(previewJobId);

  const cloneAvailable = runtime?.supports_voice_cloning === true;
  const sourceDuration =
    analysis?.source_duration_seconds ?? analysis?.duration_seconds ?? 0;
  const selectedStart =
    selectedSegment?.start ?? analysis?.selected_start_seconds ?? 0;
  const selectedEnd =
    selectedSegment?.end ?? analysis?.selected_end_seconds ?? 0;
  const cloneAnalysis = analysis && {
    ...analysis,
    selected_start_seconds: selectedStart,
    selected_end_seconds: selectedEnd,
  };
  const referenceTextPolicy = runtime?.reference_text_policy ?? "optional";
  const referenceTextUsedForEnrollment =
    runtime?.reference_text_used_for_enrollment === true;
  const referenceMinSeconds = runtime?.reference_min_seconds ?? 3;
  const referenceMaxSeconds = runtime?.reference_max_seconds ?? 8;
  const transcriptVisible = referenceTextPolicy !== "ignored";
  const transcriptRequired = referenceTextPolicy === "required";
  const currentSegmentKey = `${selectedStart.toFixed(2)}:${selectedEnd.toFixed(2)}`;

  useEffect(() => {
    if (!transcriptSegmentKey) return;
    if (currentSegmentKey !== transcriptSegmentKey) {
      setTranscriptNeedsReview(true);
    }
  }, [currentSegmentKey, transcriptSegmentKey, setTranscriptNeedsReview]);

  const readableError = (error: unknown, fallback: string) =>
    error instanceof Error && error.message ? error.message : fallback;

  const playSelection = () => {
    const audio = sourceAudioRef.current;
    if (!audio || !selectedEnd || selectedEnd <= selectedStart) return;
    audio.currentTime = selectedStart;
    void audio.play();
  };

  const handleAutoPickBestSegment = () => {
    if (!analysis) return;
    const start = analysis.recommended_start_seconds ?? analysis.selected_start_seconds ?? 0;
    const end = analysis.recommended_end_seconds ?? analysis.selected_end_seconds ?? Math.min(sourceDuration, 6);
    setSelectedSegment({ start, end });
    toast.success(`${t("voiceLab.autoBestSegment")}: ${start.toFixed(1)}s – ${end.toFixed(1)}s`);
  };

  const { isTranscribing, activeModelId, autoTranscribeInVoiceLab, transcribeAudioSegment } = useSpeechModelsStore();

  const handleAutoTranscribe = async () => {
    if (!file) return;
    try {
      const text = await transcribeAudioSegment({
        audioFile: file,
        startSeconds: selectedStart,
        endSeconds: selectedEnd,
      });
      if (text) {
        setReferenceTranscript(text);
        setTranscriptSegmentKey(currentSegmentKey);
        setTranscriptNeedsReview(false);
        toast.success(t("voiceLab.transcribeSuccess"));
      } else {
        toast.info(t("voiceLab.transcribeEmpty"));
      }
    } catch {
      toast.error(t("voiceLab.transcribeEmpty"));
    }
  };

  const hasAutoTranscribedRef = useRef<string | null>(null);
  useEffect(() => {
    if (!analysis || !file || isTranscribing || !autoTranscribeInVoiceLab) return;
    const segmentKey = `${selectedStart.toFixed(1)}:${selectedEnd.toFixed(1)}`;
    if (hasAutoTranscribedRef.current === segmentKey) return;
    hasAutoTranscribedRef.current = segmentKey;
    void handleAutoTranscribe();
  }, [analysis, file, selectedStart, selectedEnd, autoTranscribeInVoiceLab]);

  const handleAudioTimeUpdate = (event: SyntheticEvent<HTMLAudioElement>) => {
    const audio = event.currentTarget;
    if (selectedEnd > selectedStart && audio.currentTime >= selectedEnd) {
      audio.pause();
      audio.currentTime = selectedStart;
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0], {
      formatError: t("voiceLab.errorAudioFormat"),
      sizeError: t("voiceLab.errorAudioSize"),
    });
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) =>
    selectFile(event.target.files?.[0], {
      formatError: t("voiceLab.errorAudioFormat"),
      sizeError: t("voiceLab.errorAudioSize"),
    });

  const handleCreateProfile = async () => {
    await startClone({
      queryClient,
      stages: {
        upload: t("voiceLab.stageUpload"),
        analyze: t("voiceLab.stageAnalyze"),
        extract: t("voiceLab.stageExtract"),
        saving: t("voiceLab.stageSaving"),
        completed: t("voiceLab.stageCompleted"),
        successToast: t("voiceLab.profileCreatedSuccess"),
        errorToast: t("voiceLab.errorCreatingProfile"),
      },
    });
  };

  const generatePreview = async () => {
    if (!profile || !previewText.trim()) return;
    setPreviewError(null);
    try {
      const response = await apiFetch<BatchJobCreateResponse>(
        "/api/v1/tts/jobs",
        {
          method: "POST",
          body: JSON.stringify({
            text: previewText,
            voiceType: profile.id,
            rate: Number(previewRate),
            providerId: profile.provider_id,
          }),
        },
      );
      setPreviewJobId(response.jobs[0]?.id ?? null);
    } catch (error) {
      setPreviewError(readableError(error, t("voiceLab.errorQueuePreview")));
    }
  };

  const [previewAudioBlobUrl, setPreviewAudioBlobUrl] = useState<string | null>(null);
  const [isLoadingPreviewAudio, setIsLoadingPreviewAudio] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [calibrationAudioBlobUrl, setCalibrationAudioBlobUrl] = useState<string | null>(null);
  const [isCalibPlaying, setIsCalibPlaying] = useState(false);
  const [calibCurrentTime, setCalibCurrentTime] = useState(0);
  const [calibDuration, setCalibDuration] = useState(0);
  const calibAudioRef = useRef<HTMLAudioElement>(null);

  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const [previewCurrentTime, setPreviewCurrentTime] = useState(0);
  const [previewDuration, setPreviewDuration] = useState(0);
  const previewAudioRef = useRef<HTMLAudioElement>(null);

  const togglePlayCalib = () => {
    const audio = calibAudioRef.current;
    if (!audio) return;
    if (isCalibPlaying) {
      audio.pause();
    } else {
      void audio.play();
    }
  };

  const handleCalibSeek = (e: ChangeEvent<HTMLInputElement>) => {
    const audio = calibAudioRef.current;
    if (!audio) return;
    const time = Number(e.target.value);
    audio.currentTime = time;
    setCalibCurrentTime(time);
  };

  const togglePlayPreview = () => {
    const audio = previewAudioRef.current;
    if (!audio) return;
    if (isPreviewPlaying) {
      audio.pause();
    } else {
      void audio.play();
    }
  };

  const handlePreviewSeek = (e: ChangeEvent<HTMLInputElement>) => {
    const audio = previewAudioRef.current;
    if (!audio) return;
    const time = Number(e.target.value);
    audio.currentTime = time;
    setPreviewCurrentTime(time);
  };

  // Load calibration audio blob reliably through apiFetchBlob
  useEffect(() => {
    if (profile?.id && profile.calibration_available) {
      let isSubscribed = true;
      apiFetchBlob(`/api/v1/tts/voices/custom/${profile.id}/calibration/audio`)
        .then((blob) => {
          if (!isSubscribed) return;
          const url = URL.createObjectURL(blob);
          setCalibrationAudioBlobUrl((prev) => {
            if (prev && typeof URL.revokeObjectURL === "function") {
              URL.revokeObjectURL(prev);
            }
            return url;
          });
        })
        .catch((err) => {
          console.error("Failed to load calibration audio blob", err);
        });

      return () => {
        isSubscribed = false;
      };
    } else {
      setCalibrationAudioBlobUrl(null);
    }
  }, [profile?.id, profile?.calibration_available]);

  // Load preview audio blob reliably through apiFetchBlob
  useEffect(() => {
    if (previewJob?.status === "completed" && previewJob.id) {
      let isSubscribed = true;
      setIsLoadingPreviewAudio(true);
      apiFetchBlob(`/api/v1/tts/jobs/${previewJob.id}/audio`)
        .then((blob) => {
          if (!isSubscribed) return;
          const url = URL.createObjectURL(blob);
          setPreviewAudioBlobUrl((prev) => {
            if (prev && typeof URL.revokeObjectURL === "function") {
              URL.revokeObjectURL(prev);
            }
            return url;
          });
        })
        .catch((err) => {
          console.error("Failed to load preview audio blob", err);
          toast.error("Không thể tải file âm thanh nghe thử");
        })
        .finally(() => {
          if (isSubscribed) setIsLoadingPreviewAudio(false);
        });

      return () => {
        isSubscribed = false;
      };
    } else if (previewJob?.status === "processing" || previewJob?.status === "queued") {
      setPreviewAudioBlobUrl(null);
    }
  }, [previewJob?.status, previewJob?.id]);

  useEffect(() => {
    return () => {
      if (previewAudioBlobUrl && typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(previewAudioBlobUrl);
      }
    };
  }, [previewAudioBlobUrl]);

  const handleDownloadPreview = async (format: "wav" | "mp3" | "m4a") => {
    if (!previewJob?.id) return;
    setDownloadingFormat(format);
    try {
      const endpoint = format === "wav"
        ? `/api/v1/tts/jobs/${previewJob.id}/audio?format=wav`
        : format === "m4a"
          ? `/api/v1/tts/jobs/${previewJob.id}/audio?format=m4a`
          : `/api/v1/tts/jobs/${previewJob.id}/audio`;
      const blob = await apiFetchBlob(endpoint);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const baseName = profile?.display_name ? `preview_${profile.display_name}` : `preview_${previewJob.id.slice(0, 8)}`;
      a.download = `${baseName}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      if (typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(url);
      }
      toast.success(`Đã tải file ${format.toUpperCase()} thành công`);
    } catch (err) {
      console.error("Failed to download audio", err);
      toast.error("Không thể tải file âm thanh");
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="mb-5 flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.18em] text-primary/60">
            VieNeu / local audio
          </p>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("voiceLab.title")}
          </h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            {t("voiceLab.subtitle")}
          </p>
        </div>
        <RuntimeBadge
          isLoading={capabilities.isLoading}
          available={cloneAvailable}
          reason={runtime?.reason}
        />
      </header>

      <div className="mb-5 flex shrink-0 justify-end">
        <span className="hidden text-xs text-muted-foreground sm:block">
          V3 Turbo · 48 kHz
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-5">
            {/* STEP 1 */}
            <StepCard step="1" title={t("voiceLab.step1Title")}>
              <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={onDrop}
                className={`rounded-xl border border-dashed p-5 text-center transition-colors ${file ? "border-primary/40 bg-primary/[0.03]" : "border-border bg-muted/30 hover:border-primary/50"}`}
              >
                <input
                  ref={fileInputRef}
                  id="voice-sample-file"
                  aria-label="Voice sample file"
                  type="file"
                  accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4"
                  onChange={onFileChange}
                  className="sr-only"
                />
                {file ? (
                  <div className="flex items-center justify-between gap-3 text-left">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <FileAudio className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold">
                          {file.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatBytes(file.size)} · {t("voiceLab.localOnly")}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => selectFile(null)}
                      className="shrink-0 text-xs font-semibold text-muted-foreground underline underline-offset-2 hover:text-foreground"
                    >
                      {t("voiceLab.replaceFile")}
                    </button>
                  </div>
                ) : (
                  <>
                    <Upload className="mx-auto h-6 w-6 text-primary/70" />
                    <p className="mt-3 text-sm font-semibold">
                      {t("voiceLab.step1Dropzone")}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t("voiceLab.step1Formats")}
                    </p>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="mt-4 rounded-lg border border-border bg-card px-4 py-2 text-xs font-bold shadow-xs hover:bg-muted"
                    >
                      {t("voiceLab.step1Browse")}
                    </button>
                  </>
                )}
              </div>
              {fileUrl && (
                <div className="mt-3 rounded-xl border border-border bg-card p-3">
                  <p className="mb-2 text-xs font-semibold text-muted-foreground">
                    {t("voiceLab.sourcePlayback")}
                  </p>
                  <audio
                    ref={sourceAudioRef}
                    className="w-full"
                    controls
                    src={fileUrl}
                    onTimeUpdate={handleAudioTimeUpdate}
                  />
                </div>
              )}
              {fileError && (
                <p
                  className="mt-3 text-xs font-semibold text-destructive"
                  role="alert"
                >
                  {fileError}
                </p>
              )}
              <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span>{t("voiceLab.localPrivacyNotice")}</span>
              </div>
            </StepCard>

            {/* STEP 2 */}
            <StepCard step="2" title={t("voiceLab.step2Title")}>
              {file ? (
                <>
                  <div className="mb-3 flex flex-wrap gap-2 text-xs">
                    <span
                      className={`rounded-full px-2.5 py-1 font-semibold ${analysisError ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400" : isAnalyzing ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400" : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"}`}
                    >
                      {analysisError
                        ? t("voiceLab.analysisFailed")
                        : isAnalyzing
                          ? t("voiceLab.analysisPending")
                          : analysis
                            ? t("voiceLab.analysisReady")
                            : t("voiceLab.analysisWaiting")}
                    </span>
                    <span className="rounded-full bg-muted px-2.5 py-1 font-semibold text-muted-foreground">
                      {t("voiceLab.selectedSegment")}{" "}
                      {analysis
                        ? `${selectedStart.toFixed(1)}–${selectedEnd.toFixed(1)}s`
                        : "—"}
                    </span>
                  </div>
                  {analysisError && (
                    <p
                      className="mb-3 text-xs font-semibold text-destructive"
                      role="alert"
                    >
                      {analysisError || t("voiceLab.analysisSampleLengthError")}
                    </p>
                  )}
                  <Waveform peaks={analysis?.waveform_peaks} />
                  {analysis && (
                    <div className="mt-4 rounded-xl border border-border bg-muted/20 p-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold">
                          {t("voiceLab.referenceSegment")}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-primary">
                            {selectedEnd - selectedStart > 0
                              ? `${(selectedEnd - selectedStart).toFixed(1)}s`
                              : "—"}{" "}
                            · 3–8s
                          </span>
                          <button
                            type="button"
                            onClick={handleAutoPickBestSegment}
                            className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-[11px] font-bold text-primary hover:bg-primary/20 transition-colors"
                          >
                            <Sparkles className="h-3 w-3" />
                            {t("voiceLab.autoBestSegment")}
                          </button>
                        </div>
                      </div>
                      <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>0.0s</span>
                        <span>
                          {t("voiceLab.sourceDurationLabel", {
                            duration: sourceDuration.toFixed(1),
                          })}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={playSelection}
                        disabled={!fileUrl || selectedEnd <= selectedStart}
                        className="mt-3 rounded-lg border border-border bg-card px-3 py-2 text-xs font-bold disabled:opacity-40"
                      >
                        {t("voiceLab.playSelectedSegment")}
                      </button>
                      <label className="mt-3 block text-xs text-muted-foreground">
                        {t("voiceLab.startLabel")} {selectedStart.toFixed(1)}s
                        <input
                          aria-label="Reference segment start"
                          type="range"
                          min="0"
                          max={Math.max(
                            0,
                            Math.min(selectedEnd - 3, sourceDuration - 3),
                          )}
                          step="0.1"
                          value={selectedStart}
                          onChange={(event) =>
                            setSelectedSegment({
                              start: Math.min(
                                Number(event.target.value),
                                selectedEnd - 3,
                              ),
                              end: selectedEnd,
                            })
                          }
                          className="mt-2 w-full accent-primary"
                        />
                      </label>
                      <label className="mt-3 block text-xs text-muted-foreground">
                        {t("voiceLab.endLabel")} {selectedEnd.toFixed(1)}s
                        <input
                          aria-label="Reference segment end"
                          type="range"
                          min={Math.min(sourceDuration, selectedStart + 3)}
                          max={Math.min(sourceDuration, selectedStart + 8)}
                          step="0.1"
                          value={selectedEnd}
                          onChange={(event) =>
                            setSelectedSegment({
                              start: selectedStart,
                              end: Number(event.target.value),
                            })
                          }
                          className="mt-2 w-full accent-primary"
                        />
                      </label>
                    </div>
                  )}
                  <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                    {[
                      [
                        t("voiceLab.speechLabel"),
                        analysis
                          ? `${Math.round(analysis.speech_ratio * 100)}%`
                          : "—",
                      ],
                      [
                        t("voiceLab.noiseLabel"),
                        analysis ? `${analysis.noise_level_db} dB` : "—",
                      ],
                      [
                        t("voiceLab.clippingLabel"),
                        analysis
                          ? `${(analysis.clipping_ratio * 100).toFixed(1)}%`
                          : "—",
                      ],
                      [
                        t("voiceLab.qualityLabel"),
                        analysis ? `${analysis.quality_score}/100` : "—",
                      ],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        className="rounded-xl bg-card border border-border/60 p-2.5"
                      >
                        <p className="text-muted-foreground text-[11px]">
                          {label}
                        </p>
                        <p className="mt-1 font-bold text-foreground text-sm">
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* V2 Metrics Detail (SNR, Noise Floor, Stability) */}
                  {analysis && (
                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                      <div className="rounded-lg bg-muted/30 border border-border/40 p-2 text-center">
                        <span className="text-[10px] text-muted-foreground block">{t("voiceLab.snrLabel")}</span>
                        <span className="font-bold text-xs">{analysis.estimated_snr_db ?? "—"} dB</span>
                      </div>
                      <div className="rounded-lg bg-muted/30 border border-border/40 p-2 text-center">
                        <span className="text-[10px] text-muted-foreground block">{t("voiceLab.noiseFloorLabel")}</span>
                        <span className="font-bold text-xs">{analysis.noise_floor_dbfs ?? "—"} dBFS</span>
                      </div>
                      <div className="rounded-lg bg-muted/30 border border-border/40 p-2 text-center">
                        <span className="text-[10px] text-muted-foreground block">{t("voiceLab.stabilityLabel")}</span>
                        <span className="font-bold text-xs">
                          {analysis.level_stability != null ? `${Math.round(analysis.level_stability * 100)}%` : "—"}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Reference transcript (engine-aware policy: ignored/optional/required) */}
                  {transcriptVisible && analysis && (
                    <div className="mt-4 rounded-xl border border-border bg-muted/20 p-3">
                      <div className="flex items-center justify-between">
                        <label
                          htmlFor="reference-transcript"
                          className="text-xs font-semibold"
                        >
                          {t("voiceLab.referenceTranscriptLabel")}
                          {transcriptRequired
                            ? ` · ${t("voiceLab.referenceTranscriptRequired")}`
                            : ` · ${t("voiceLab.referenceTranscriptOptional")}`}
                        </label>
                        <button
                          type="button"
                          onClick={() => void handleAutoTranscribe()}
                          disabled={isTranscribing || !file}
                          className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary hover:bg-primary/20 transition-colors disabled:opacity-50 shadow-2xs"
                          title={`Whisper (${activeModelId})`}
                        >
                          {isTranscribing ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Sparkles className="h-3 w-3" />
                          )}
                          <span>{t("voiceLab.autoTranscribeBtn")}</span>
                        </button>
                      </div>
                      <textarea
                        id="reference-transcript"
                        value={referenceTranscript}
                        onChange={(event) => {
                          setReferenceTranscript(event.target.value);
                          if (!transcriptSegmentKey) {
                            setTranscriptSegmentKey(currentSegmentKey);
                          }
                        }}
                        onFocus={() => {
                          if (!transcriptSegmentKey) {
                            setTranscriptSegmentKey(currentSegmentKey);
                          }
                        }}
                        placeholder={t("voiceLab.referenceTranscriptPlaceholder")}
                        className="mt-2 min-h-20 w-full resize-y rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none focus:border-primary"
                      />
                      <p className="mt-2 text-[11px] text-muted-foreground">
                        {t("voiceLab.referenceTranscriptHelper", {
                          start: selectedStart.toFixed(1),
                          end: selectedEnd.toFixed(1),
                        })}
                      </p>
                      {!referenceTextUsedForEnrollment && (
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          {t("voiceLab.referenceTranscriptV3Note")}
                        </p>
                      )}
                      {transcriptNeedsReview && referenceTranscript && (
                        <p
                          role="status"
                          className="mt-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 px-3 py-2 text-[11px] font-semibold text-amber-700 dark:text-amber-400"
                        >
                          {t("voiceLab.referenceTranscriptReviewWarning")}
                        </p>
                      )}
                      {transcriptRequired &&
                        !referenceTranscript.trim() && (
                          <p
                            role="alert"
                            className="mt-2 text-[11px] font-semibold text-destructive"
                          >
                            {t("voiceLab.referenceTranscriptRequiredValidation")}
                          </p>
                        )}
                    </div>
                  )}

                  {analysis?.warnings.map((warning) => (
                    <p
                      key={warning}
                      className="mt-3 text-xs font-semibold text-amber-700 dark:text-amber-400"
                    >
                      {warning}
                    </p>
                  ))}
                </>
              ) : (
                <div className="flex min-h-24 items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 text-center text-sm text-muted-foreground">
                  {t("voiceLab.uploadSampleHint")}
                </div>
              )}
            </StepCard>

            {/* STEP 3 */}
            <StepCard step="3" title={t("voiceLab.step3Title")}>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-xs font-semibold">
                  {t("voiceLab.voiceNameLabel")}
                  <input
                    value={voiceName}
                    onChange={(event) => setVoiceName(event.target.value)}
                    placeholder={t("voiceLab.voiceNamePlaceholder")}
                    className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none ring-primary/20 focus:ring-4"
                  />
                </label>
                <label className="text-xs font-semibold">
                  {t("voiceLab.languageLabel")}
                  <input
                    value={t("voiceLab.langVietnamese")}
                    readOnly
                    className="mt-2 w-full rounded-lg border border-border bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground outline-none"
                  />
                </label>
              </div>

              {/* V2 Options: Denoise & Clone Mode */}
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="text-xs font-semibold">
                  {t("voiceLab.denoiseModeLabel")}
                  <select
                    value={denoiseMode}
                    onChange={(e) => setDenoiseMode(e.target.value as "auto" | "off" | "on")}
                    className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs cursor-pointer outline-none focus:border-primary"
                  >
                    <option value="auto">{t("voiceLab.denoiseAuto")}</option>
                    <option value="off">{t("voiceLab.denoiseOff")}</option>
                    <option value="on">{t("voiceLab.denoiseOn")}</option>
                  </select>
                </label>
                <label className="text-xs font-semibold">
                  {t("voiceLab.cloneModeLabel")}
                  <select
                    value={cloneMode}
                    onChange={(e) => setCloneMode(e.target.value as "fidelity" | "stability")}
                    className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs cursor-pointer outline-none focus:border-primary"
                  >
                    <option value="fidelity">{t("voiceLab.cloneFidelity")}</option>
                    <option value="stability">{t("voiceLab.cloneStability")}</option>
                  </select>
                </label>
              </div>

              <div className="mt-4 flex items-center justify-between rounded-xl border border-border bg-muted/30 p-3 text-xs">
                <span className="font-semibold">
                  {t("voiceLab.engineLabel")}
                </span>
                <span className="font-bold">
                  VieNeu v3 Turbo · {runtime?.backend ?? "—"}
                </span>
              </div>
              <label className="mt-4 flex items-start gap-3 text-xs leading-5 text-muted-foreground">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  className="mt-1 h-4 w-4 accent-primary"
                />
                <span>{t("voiceLab.consentText")}</span>
              </label>
              <button
                type="button"
                onClick={() => void handleCreateProfile()}
                disabled={
                  !cloneAvailable ||
                  !file ||
                  !cloneAnalysis ||
                  !voiceName.trim() ||
                  !consent ||
                  (transcriptRequired && !referenceTranscript.trim()) ||
                  isCloning
                }
                className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-primary-foreground transition-opacity disabled:cursor-not-allowed disabled:opacity-40 shadow-xs"
              >
                {isCloning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <UserRoundPlus className="h-4 w-4" />
                )}
                <span>
                  {isCloning
                    ? t("voiceLab.creatingVoice")
                    : t("voiceLab.createVoiceBtn")}
                </span>
              </button>

              {/* Progress bar during cloning */}
              {isCloning && (
                <div className="mt-4 space-y-2 rounded-xl border border-primary/25 bg-primary/5 p-3.5 animate-in fade-in slide-in-from-top-1 duration-200">
                  <div className="flex items-center justify-between text-xs font-bold text-primary">
                    <span className="flex items-center gap-1.5">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      {cloneStage}
                    </span>
                    <span className="font-mono text-xs">{cloneProgress}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-primary/15">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                      style={{ width: `${cloneProgress}%` }}
                    />
                  </div>
                </div>
              )}
              {!cloneAvailable && (
                <p className="mt-3 text-xs font-semibold text-amber-700 dark:text-amber-400">
                  {runtime?.reason ?? t("voiceLab.checkingCloneCapability")}
                </p>
              )}
              {cloneError && (
                <p
                  className="mt-3 text-xs font-semibold text-destructive"
                  role="alert"
                >
                  {cloneError}
                </p>
              )}
              {profile && (
                <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3.5">
                  <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                    {t("voiceLab.profileCreatedSuccess")}
                    <a href="/voices" className="underline underline-offset-2">
                      {t("voiceLab.voiceLibraryLink")}
                    </a>
                    .
                  </p>
                  <button
                    type="button"
                    onClick={reset}
                    className="shrink-0 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold text-foreground shadow-xs hover:bg-muted"
                  >
                    {t("voiceLab.createAnotherVoice")}
                  </button>
                </div>
              )}
            </StepCard>
          </div>

          {/* SIDEBAR: Preview & Output */}
          <aside className="h-fit rounded-2xl border border-border bg-card p-5 shadow-sm xl:sticky xl:top-0">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold">
                {t("voiceLab.previewOutputHeading")}
              </h2>
              <Sparkles className="h-4 w-4 text-primary/60" />
            </div>
            <div className="mt-5 space-y-4 text-sm">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <span className="text-muted-foreground">
                  {t("voiceLab.referenceSourceLabel")}
                </span>
                <span className="max-w-40 truncate font-semibold">
                  {file?.name ?? t("voiceLab.noFileSelected")}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-border pb-3">
                <span className="text-muted-foreground">
                  {t("voiceLab.selectedDurationLabel")}
                </span>
                <span className="font-semibold">
                  {selectedEnd > selectedStart
                    ? `${(selectedEnd - selectedStart).toFixed(1)}s`
                    : "—"}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-border pb-3">
                <span className="text-muted-foreground">
                  {t("voiceLab.referenceTranscriptLabel")}
                </span>
                <span className="max-w-40 truncate text-xs text-muted-foreground">
                  {(referenceTranscript.trim() || profile?.transcript)
                    ? (referenceTranscript.trim() || profile?.transcript || "")
                    : t("voiceLab.transcriptPlaceholderAuto")}
                </span>
              </div>

              {/* Similarity score */}
              {profile?.speaker_similarity_score != null && (
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <span className="text-muted-foreground">{t("voiceLab.similarityLabel")}</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">
                    {Math.round(profile.speaker_similarity_score * 100)}%
                  </span>
                </div>
              )}

              {/* Calibration audio player */}
              {profile && profile.calibration_available && (
                <div className="rounded-xl border border-primary/25 bg-gradient-to-br from-primary/[0.07] via-background to-primary/[0.02] p-4 shadow-xs space-y-3">
                  {/* Card Title & Icon */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Volume2 className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-foreground">
                          {t("voiceLab.calibrationAudioLabel")}
                        </h4>
                        <p className="text-[10px] text-muted-foreground">Mẫu kiểm thử âm sắc chuẩn</p>
                      </div>
                    </div>
                  </div>

                  {/* 2-Column Stats Bar */}
                  <div className="grid grid-cols-2 gap-2">
                    {profile.calibration_quality_score != null && (
                      <div
                        title="Độ trong trẻo, âm lượng RMS chuẩn, không vỡ tiếng của âm thanh AI tạo ra: 0-100"
                        className="flex items-center justify-between rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 cursor-help"
                      >
                        <span className="text-[10px] font-medium text-muted-foreground">Chất lượng AI</span>
                        <span className="text-[11px] font-mono font-bold text-primary">
                          {profile.calibration_quality_score}/100
                        </span>
                      </div>
                    )}
                    {profile.speaker_similarity_score != null && (
                      <div
                        title="Độ giống giọng mẫu gốc theo thuật toán Speaker Cosine Similarity (>65% là mức rất cao): 0-100%"
                        className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1.5 cursor-help"
                      >
                        <span className="text-[10px] font-medium text-muted-foreground">Độ giống giọng</span>
                        <span className="text-[11px] font-mono font-bold text-emerald-600 dark:text-emerald-400">
                          {Math.round(profile.speaker_similarity_score * 100)}%
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Audio Element & Custom Player Controls */}
                  <audio
                    ref={calibAudioRef}
                    src={calibrationAudioBlobUrl || undefined}
                    onPlay={() => setIsCalibPlaying(true)}
                    onPause={() => setIsCalibPlaying(false)}
                    onTimeUpdate={(e) => setCalibCurrentTime(e.currentTarget.currentTime)}
                    onLoadedMetadata={(e) => setCalibDuration(e.currentTarget.duration)}
                    onEnded={() => {
                      setIsCalibPlaying(false);
                      setCalibCurrentTime(0);
                    }}
                    preload="auto"
                  />

                  <div className="flex items-center gap-3 rounded-lg border border-border/80 bg-card/80 p-2.5">
                    <button
                      type="button"
                      onClick={togglePlayCalib}
                      disabled={!calibrationAudioBlobUrl}
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 transition-all active:scale-95 disabled:opacity-50"
                      title={isCalibPlaying ? "Tạm dừng" : "Phát mẫu chuẩn"}
                    >
                      {isCalibPlaying ? (
                        <Pause className="h-4 w-4 fill-current" />
                      ) : (
                        <Play className="h-4 w-4 fill-current ml-0.5" />
                      )}
                    </button>

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
                        <span>{calibCurrentTime.toFixed(1)}s</span>
                        <span>{calibDuration > 0 ? `${calibDuration.toFixed(1)}s` : "—"}</span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={calibDuration || 100}
                        step={0.1}
                        value={calibCurrentTime}
                        onChange={handleCalibSeek}
                        disabled={!calibrationAudioBlobUrl || calibDuration <= 0}
                        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary disabled:cursor-not-allowed"
                      />
                    </div>
                  </div>

                  <p className="text-[10px] text-muted-foreground italic px-1">
                    "Xin chào, đây là voice clone được tạo từ Void Melody."
                  </p>
                </div>
              )}

              {selectedProfile.isLoading && (
                <p className="text-xs text-muted-foreground">
                  {t("voiceLab.loadingProfile")}
                </p>
              )}
              {selectedProfile.isError && (
                <p className="rounded-xl bg-red-50 dark:bg-red-950/40 p-3 text-xs font-semibold text-destructive">
                  {t("voiceLab.errorLoadingProfile")}
                </p>
              )}
              <div className="rounded-xl bg-muted/50 p-4">
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  {t("voiceLab.profileStatus")}
                </p>
                <p className="mt-2 text-sm font-bold text-foreground">
                  {profile?.display_name ?? t("voiceLab.noProfileYet")}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {profile
                    ? t("voiceLab.profileReadyDesc")
                    : t("voiceLab.createProfileToUnlockDesc")}
                </p>
              </div>
              {previewJobError && (
                <p className="rounded-xl bg-red-50 dark:bg-red-950/40 p-3 text-xs font-semibold text-destructive">
                  {t("voiceLab.errorLoadingPreviewStatus")}
                </p>
              )}
              {previewError && (
                <p
                  className="rounded-xl bg-red-50 dark:bg-red-950/40 p-3 text-xs font-semibold text-destructive"
                  role="alert"
                >
                  {previewError}
                </p>
              )}
              {previewJob && (
                <div className="rounded-xl border border-border/80 bg-gradient-to-b from-card to-muted/20 p-4 space-y-3.5 shadow-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <p className="text-xs font-bold uppercase tracking-wider text-foreground">
                        {t("voiceLab.previewTitle")}
                      </p>
                    </div>
                    {(previewJob.status === "processing" || previewJob.status === "queued") ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-bold text-primary animate-pulse">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        {t("jobQueue.statusGenerating")}
                      </span>
                    ) : previewJob.status === "completed" ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                        <Check className="h-3 w-3" /> Sẵn sàng
                      </span>
                    ) : null}
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {previewJob.status === "completed"
                      ? t("voiceLab.previewReadyDesc")
                      : previewJob.status === "failed"
                        ? (previewJob.errorMessage ?? t("voiceLab.analysisFailed"))
                        : `${t("voiceLab.generatingPreview")} (${previewJob.status})...`}
                  </p>

                  {previewJob.status === "completed" && (
                    <div className="space-y-3 pt-1">
                      {isLoadingPreviewAudio ? (
                        <div className="flex items-center justify-center gap-2 py-5 text-xs text-muted-foreground bg-muted/30 rounded-xl border border-border/60">
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          <span>{t("voiceLab.loadingAudioFile")}</span>
                        </div>
                      ) : previewAudioBlobUrl ? (
                        <div className="rounded-xl border border-primary/20 bg-background/80 p-3 space-y-2 shadow-xs">
                          {/* Hidden audio element */}
                          <audio
                            ref={previewAudioRef}
                            src={previewAudioBlobUrl}
                            onPlay={() => setIsPreviewPlaying(true)}
                            onPause={() => setIsPreviewPlaying(false)}
                            onTimeUpdate={(e) => setPreviewCurrentTime(e.currentTarget.currentTime)}
                            onLoadedMetadata={(e) => setPreviewDuration(e.currentTarget.duration)}
                            onEnded={() => {
                              setIsPreviewPlaying(false);
                              setPreviewCurrentTime(0);
                            }}
                            preload="auto"
                          />

                          {/* Custom Player Controller */}
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={togglePlayPreview}
                              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 transition-all active:scale-95 cursor-pointer"
                              title={isPreviewPlaying ? "Tạm dừng" : "Phát âm thanh"}
                            >
                              {isPreviewPlaying ? (
                                <Pause className="h-4 w-4 fill-current" />
                              ) : (
                                <Play className="h-4 w-4 fill-current ml-0.5" />
                              )}
                            </button>

                            <div className="flex-1 space-y-1.5">
                              <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                                <span className="font-semibold text-foreground">{previewCurrentTime.toFixed(1)}s</span>
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
                                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary disabled:cursor-not-allowed"
                              />
                            </div>
                          </div>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            if (previewJob.id) {
                              setIsLoadingPreviewAudio(true);
                              apiFetchBlob(`/api/v1/tts/jobs/${previewJob.id}/audio`)
                                .then((blob) => {
                                  setPreviewAudioBlobUrl(URL.createObjectURL(blob));
                                })
                                .catch(() => toast.error(t("errors.previewFailed")))
                                .finally(() => setIsLoadingPreviewAudio(false));
                            }
                          }}
                          className="w-full rounded-xl border border-border bg-card py-2.5 text-xs font-bold hover:bg-muted transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          <span>{t("voiceLab.reloadAudioPlayer")}</span>
                        </button>
                      )}

                      {/* Export & Download Section */}
                      <div className="pt-2 border-t border-border/60">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[11px] font-bold text-muted-foreground">
                            {t("voiceLab.downloadAudioFiles")}
                          </span>
                          <span className="text-[10px] text-muted-foreground font-mono">24kHz PCM / MP3</span>
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          <button
                            type="button"
                            onClick={() => void handleDownloadPreview("wav")}
                            disabled={downloadingFormat !== null}
                            className="rounded-lg border border-border bg-background py-1.5 text-xs font-bold hover:border-primary/50 hover:bg-primary/5 transition-all inline-flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-2xs"
                          >
                            {downloadingFormat === "wav" ? <Loader2 className="h-3 w-3 animate-spin text-primary" /> : <Download className="h-3 w-3 text-primary" />}
                            <span>WAV</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDownloadPreview("mp3")}
                            disabled={downloadingFormat !== null}
                            className="rounded-lg border border-border bg-background py-1.5 text-xs font-bold hover:border-primary/50 hover:bg-primary/5 transition-all inline-flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-2xs"
                          >
                            {downloadingFormat === "mp3" ? <Loader2 className="h-3 w-3 animate-spin text-primary" /> : <Download className="h-3 w-3 text-primary" />}
                            <span>MP3</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDownloadPreview("m4a")}
                            disabled={downloadingFormat !== null}
                            className="rounded-lg border border-border bg-background py-1.5 text-xs font-bold hover:border-primary/50 hover:bg-primary/5 transition-all inline-flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-2xs"
                          >
                            {downloadingFormat === "m4a" ? <Loader2 className="h-3 w-3 animate-spin text-primary" /> : <Download className="h-3 w-3 text-primary" />}
                            <span>M4A</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </aside>
        </div>

        {/* Test synthesis & Studio Quick Start section */}
        <section className="mt-6 rounded-2xl border border-primary/20 bg-gradient-to-b from-card via-card to-primary/[0.02] p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-foreground">
                  {t("voiceLab.useInStudio")}
                </h2>
                <p className="text-xs text-muted-foreground">
                  Thử nghiệm tạo giọng đọc AI từ văn bản tùy ý hoặc chuyển tiếp trực tiếp vào Studio
                </p>
              </div>
            </div>

            {profile && (
              <a
                href={`/generate?voice=${profile.id}`}
                className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-xl border border-primary/30 bg-primary/5 px-3.5 py-1.5 text-xs font-bold text-primary hover:bg-primary/10 transition-colors"
              >
                <span>Mở trong Studio</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>

          {/* Quick preset chips */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" /> Mẫu nhanh:
            </span>
            {referenceTranscript.trim() && (
              <button
                type="button"
                onClick={() => setPreviewText(referenceTranscript.trim())}
                disabled={!profile}
                className="rounded-lg border border-border/80 bg-background/80 px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 cursor-pointer"
              >
                🎙️ Lời thoại gốc
              </button>
            )}
            <button
              type="button"
              onClick={() => setPreviewText("Xin chào các bạn, hôm nay tôi sẽ hướng dẫn các bạn cách ứng dụng trí tuệ nhân tạo để làm việc hiệu quả hơn.")}
              disabled={!profile}
              className="rounded-lg border border-border/80 bg-background/80 px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 cursor-pointer"
            >
              👋 Lời chào
            </button>
            <button
              type="button"
              onClick={() => setPreviewText("Đêm ấy, ánh trăng chiếu rọi xuống mặt hồ phẳng lặng như gương. Gió thu se lạnh khẽ lướt qua rặng liễu ven bờ.")}
              disabled={!profile}
              className="rounded-lg border border-border/80 bg-background/80 px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 cursor-pointer"
            >
              📖 Kể chuyện
            </button>
            <button
              type="button"
              onClick={() => setPreviewText("Bản tin công nghệ: Mô hình giọng nói AI cục bộ đang thay đổi hoàn toàn quy trình sáng tạo âm thanh và lồng tiếng video.")}
              disabled={!profile}
              className="rounded-lg border border-border/80 bg-background/80 px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 cursor-pointer"
            >
              📰 Tin tức
            </button>
          </div>

          <div className="mt-3 space-y-4">
            {/* Textarea container */}
            <div className="relative rounded-xl border border-border bg-background transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <textarea
                value={previewText}
                onChange={(event) => setPreviewText(event.target.value)}
                disabled={!profile}
                maxLength={500}
                placeholder={
                  profile
                    ? t("voiceLab.previewTextPlaceholder")
                    : t("voiceLab.createProfileToUnlockDesc")
                }
                className="min-h-24 w-full resize-y bg-transparent p-3.5 text-sm outline-none placeholder:text-muted-foreground/60 disabled:cursor-not-allowed"
              />
              <div className="flex items-center justify-between border-t border-border/50 bg-muted/20 px-3 py-1.5 text-[11px] text-muted-foreground">
                <span>Nhập tối đa 500 ký tự cho bản nghe thử</span>
                <span className="font-mono">{previewText.length}/500</span>
              </div>
            </div>

            {/* Bottom Bar: Speed selector and action button */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              {/* Modern Speed Pills */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1 shrink-0">
                  <Gauge className="h-3.5 w-3.5" />
                  {t("generate.speed")}:
                </span>
                <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 p-1">
                  {[
                    { label: "0.75×", value: "0.75" },
                    { label: "1.0× (Chuẩn)", value: "1" },
                    { label: "1.25×", value: "1.25" },
                    { label: "1.5×", value: "1.5" },
                    { label: "2.0×", value: "2" },
                  ].map((preset) => {
                    const isSelected = previewRate === preset.value;
                    return (
                      <button
                        key={preset.value}
                        type="button"
                        onClick={() => setPreviewRate(preset.value)}
                        disabled={!profile}
                        className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                          isSelected
                            ? "bg-primary text-primary-foreground shadow-xs font-bold"
                            : "text-muted-foreground hover:text-foreground hover:bg-background/60"
                        }`}
                      >
                        {preset.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Generate Button */}
              <button
                type="button"
                onClick={() => void generatePreview()}
                disabled={
                  !profile ||
                  !previewText.trim() ||
                  previewJob?.status === "queued" ||
                  previewJob?.status === "processing"
                }
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-sm font-bold text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-98 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                {(previewJob?.status === "queued" || previewJob?.status === "processing") ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>{t("voiceLab.synthesizing")}</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    <span>{t("voiceLab.generatePreview")}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
