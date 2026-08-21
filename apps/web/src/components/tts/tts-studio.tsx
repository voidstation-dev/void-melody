"use client";
import { useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { TextComposer } from "./text-composer";
import { VoiceSettingsPanel } from "./voice-settings-panel";
import { useVoices } from "@/hooks/use-voices";
import { useCustomVoices } from "@/hooks/use-custom-voices";
import { useQueue } from "@/hooks/use-queue";
import { useTextFileDrop } from "@/hooks/use-text-file-drop";
import { TextImportConflictDialog } from "./text-import-conflict-dialog";
import { JobQueueSidebar } from "./job-queue-sidebar";
import { BatchImportModal } from "./batch-import-modal";
import { ImportedTextFile, TextImportError } from "@/types/text-import";
import { apiFetch } from "@/lib/api-client";
import { getBatchLimitError } from "@/lib/batch-limits";
import { BatchJobCreateResponse } from "@/types/tts-job";
import { Loader2, Clipboard, FileUp, FolderOpen } from "lucide-react";
import { useTranslation } from "@/hooks/use-translation";

export function TTSStudio() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const voiceParam = searchParams.get("voice");
  const [text, setText] = useState("");
  const [prevVoiceParam, setPrevVoiceParam] = useState(voiceParam);
  const [selectedVoice, setSelectedVoice] = useState(voiceParam || "BV421_vivn_streaming");

  if (voiceParam !== prevVoiceParam) {
    setPrevVoiceParam(voiceParam);
    if (voiceParam) {
      setSelectedVoice(voiceParam);
    }
  }

  const [rate, setRate] = useState(1.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [conflictDialog, setConflictDialog] = useState<{isOpen: boolean, file: ImportedTextFile | null}>({isOpen: false, file: null});
  
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchFiles, setBatchFiles] = useState<ImportedTextFile[]>([]);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { addToQueue } = useQueue();

  const handleFiles = (files: ImportedTextFile[]) => {
    if (files.length === 0) return;
    
    if (files.length === 1 && !batchModalOpen) {
      const file = files[0];
      if (text.trim().length > 0) {
        setConflictDialog({ isOpen: true, file });
      } else {
        setText(file.text);
      }
    } else {
      setBatchFiles(files);
      setBatchModalOpen(true);
    }
  };

  const handleErrors = (errors: TextImportError[]) => {
    errors.forEach(err => alert(`Error importing ${err.fileName}: ${err.message}`));
  };

  const { isDragging, isValidDrag, dragProps, processFiles } = useTextFileDrop({
    allowMultiple: true,
    maxFileBytes: 10 * 1024 * 1024,
    onFiles: handleFiles,
    onErrors: handleErrors,
  });

  const handleFolderSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFiles(Array.from(e.target.files));
    }
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
  };

  const handleStartBatchJobs = async (
    selectedFiles: ImportedTextFile[],
    exportPath: string | null,
    exportFormat: "mp3" | "m4a"
  ) => {
    setIsSubmitting(true);
    try {
      const batchLimitError = getBatchLimitError(selectedFiles);
      if (batchLimitError) {
        alert(batchLimitError);
        return;
      }

      const items = selectedFiles.map((file) => ({
        text: file.text,
        voiceType: selectedVoice,
        rate,
        sourceFileName: file.fileName,
        exportPath: exportPath || undefined,
        exportFormat,
      }));

      const batchResponse = await apiFetch<BatchJobCreateResponse>(
        "/api/v1/tts/jobs/batch",
        {
          method: "POST",
          body: JSON.stringify({ items }),
        }
      );

      addToQueue(batchResponse.jobs);
      setBatchModalOpen(false);
    } catch (err) {
      console.error("Failed to create batch jobs: ", err);
      alert(t("errors.generateFailed"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const { data: voiceData } = useVoices();
  const { data: customVoiceData } = useCustomVoices(undefined, 1, 100);
  const currentVoiceObj = voiceData?.items?.find((v) => v.voiceType === selectedVoice);

  const handleGenerate = async () => {
    if (!text.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const response = await apiFetch<BatchJobCreateResponse>("/api/v1/tts/jobs", {
        method: "POST",
        body: JSON.stringify({
          text,
          voiceType: selectedVoice,
          resourceId: currentVoiceObj?.resourceId || undefined,
          rate,
        }),
      });
      addToQueue(response.jobs);
      setText("");
    } catch (err) {
      console.error("Job creation failed", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePaste = async () => {
    try {
      const clipboardText = await navigator.clipboard.readText();
      if (clipboardText) {
        setText(text + (text ? " " : "") + clipboardText);
      }
    } catch (err) {
      console.error("Failed to read clipboard contents: ", err);
      alert(t("generate.clipboardError"));
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length > 0) {
      processFiles(files);
    }
    e.target.value = "";
  };

  const handleReparse = (jobText: string, fileName?: string) => {
    if (text.trim().length > 0) {
      setConflictDialog({
        isOpen: true,
        file: {
          id: crypto.randomUUID(),
          text: jobText,
          fileName: fileName || t("generate.reparsedText"),
          sizeBytes: jobText.length,
          mimeType: "text/plain",
          characterCount: jobText.length,
          importedAt: new Date().toISOString(),
        },
      });
    } else {
      setText(jobText);
    }
  };

  return (
    <div className="grid h-full min-h-0 gap-6 md:grid-cols-[1fr_340px] xl:grid-cols-[1fr_380px]">
      <div className="flex flex-col h-full min-h-0 relative gap-3">
        <div className="rounded-2xl border border-border bg-card p-2 shadow-sm z-20 transition-all flex items-center justify-between">
          <div className="flex items-center gap-1">
            <button
              onClick={handlePaste}
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
              title={t("generate.pasteTooltip")}
            >
              <Clipboard className="h-4 w-4" />
              <span className="hidden sm:inline">{t("generate.paste")}</span>
            </button>

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
              title={t("generate.importFileTooltip")}
            >
              <FileUp className="h-4 w-4" />
              <span className="hidden sm:inline">{t("generate.importFile")}</span>
            </button>
            <input
              type="file"
              accept=".txt"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
            />
            
            <button
              onClick={() => folderInputRef.current?.click()}
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold text-muted-foreground hover:text-foreground hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-50"
              title={t("generate.importFolderTooltip")}
            >
              <FolderOpen className="h-4 w-4" />
              <span className="hidden sm:inline">{t("generate.importFolder")}</span>
            </button>
            <input
              type="file"
              ref={folderInputRef}
              onChange={handleFolderSelect}
              className="hidden"
              // @ts-ignore - webkitdirectory is a valid property for folder selection
              webkitdirectory=""
              directory=""
              multiple
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={isSubmitting || !text}
            className="flex items-center gap-2 rounded-xl bg-primary px-8 py-2.5 text-xs font-bold text-primary-foreground hover:opacity-90 disabled:opacity-50 shadow-xs"
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            <span>{isSubmitting ? t("generate.generating") : t("generate.generateAudio")}</span>
          </button>
        </div>
        <TextComposer
          value={text}
          onChange={setText}
          maxLength={500000}
          disabled={isSubmitting}
          isDragging={isDragging}
          isValidDrag={isValidDrag}
          dragProps={dragProps}
        />
        <TextImportConflictDialog
          isOpen={conflictDialog.isOpen}
          fileName={conflictDialog.file?.fileName || ""}
          onClose={() => setConflictDialog({ isOpen: false, file: null })}
          onReplace={() => {
            setText(conflictDialog.file?.text || "");
            setConflictDialog({ isOpen: false, file: null });
          }}
          onAppend={() => {
            setText(text + (text ? "\n\n" : "") + (conflictDialog.file?.text || ""));
            setConflictDialog({ isOpen: false, file: null });
          }}
        />
        <BatchImportModal
          isOpen={batchModalOpen}
          onClose={() => setBatchModalOpen(false)}
          files={batchFiles}
          onStartJobs={handleStartBatchJobs}
        />
      </div>
      <div className="h-full flex flex-col gap-4 min-h-0 pr-2">
        <div className="shrink-0">
          <VoiceSettingsPanel
            voices={voiceData?.items ?? []}
            customVoices={customVoiceData?.items ?? []}
            selectedVoice={selectedVoice}
            onSelectVoice={setSelectedVoice}
            rate={rate}
            onRateChange={setRate}
            onGenerate={handleGenerate}
            isSubmitting={isSubmitting}
          />
        </div>
        <JobQueueSidebar onReparse={handleReparse} />
      </div>
    </div>
  );
}
