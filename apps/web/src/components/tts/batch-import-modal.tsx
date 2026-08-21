import { useState, useEffect, useRef } from "react";
import { ImportedTextFile } from "@/types/text-import";
import {
  X,
  CheckSquare,
  Square,
  Loader2,
  FileText,
  Play,
  Eye,
  Edit3,
  GripVertical,
  Zap,
  FolderOutput,
} from "lucide-react";
import { useTauri } from "@/contexts/tauri-provider";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { useTranslation } from "@/hooks/use-translation";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { restrictToVerticalAxis, restrictToParentElement } from "@dnd-kit/modifiers";

type SortableFileItemProps = {
  file: ImportedTextFile;
  isSelected: boolean;
  isActive: boolean;
  onToggle: (id: string, e: React.MouseEvent) => void;
  onSelect: (id: string) => void;
};

function SortableFileItem({ file, isSelected, isActive, onToggle, onSelect }: SortableFileItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: file.id });

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.9 : 1,
    zIndex: isDragging ? 50 : 0,
    position: "relative" as const,
  };

  return (
    <div 
      ref={setNodeRef}
      style={style}
      onClick={() => onSelect(file.id)}
      className={`flex items-center gap-3 p-3 rounded-xl border transition-colors cursor-pointer group ${
        isActive ? "border-primary/50 bg-primary/[0.03] shadow-sm" : "border-border bg-card hover:border-border/80"
      } ${isDragging ? "shadow-xl border-primary ring-1 ring-primary/20 bg-card" : ""}`}
    >
      {/* Checkbox (independent click target) */}
      <button
        onClick={(e) => onToggle(file.id, e)}
        className="shrink-0 p-1 flex items-center justify-center text-primary hover:scale-110 transition-transform"
      >
        {isSelected ? (
          <CheckSquare className="w-5 h-5" />
        ) : (
          <Square className="w-5 h-5 text-muted-foreground" />
        )}
      </button>
      
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-sm font-bold truncate ${isActive ? "text-primary" : "text-foreground group-hover:text-primary/80 transition-colors"}`}>
            {file.fileName}
          </span>
          <span className="text-[10px] font-medium text-muted-foreground whitespace-nowrap bg-muted px-1.5 py-0.5 rounded-sm">
            {(file.sizeBytes / 1024).toFixed(1)} KB
          </span>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-1 opacity-70">
          {file.text.slice(0, 60)}...
        </p>
      </div>

      <div 
        {...attributes} 
        {...listeners}
        className="shrink-0 p-2 -mr-2 text-muted-foreground/30 hover:text-foreground cursor-grab active:cursor-grabbing touch-none"
      >
        <GripVertical className="w-5 h-5" />
      </div>
    </div>
  );
}

type BatchImportModalProps = {
  isOpen: boolean;
  onClose: () => void;
  files: ImportedTextFile[];
  onStartJobs: (selectedFiles: ImportedTextFile[], exportPath: string | null, exportFormat: "mp3" | "m4a") => void;
};

export function BatchImportModal({
  isOpen,
  onClose,
  files,
  onStartJobs,
}: BatchImportModalProps) {
  const { t, isVi } = useTranslation();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activePreviewId, setActivePreviewId] = useState<string | null>(null);
  const [localFiles, setLocalFiles] = useState<ImportedTextFile[]>([]);

  // Export settings
  const { isDesktop } = useTauri();
  const [exportPath, setExportPath] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<"mp3" | "m4a">("mp3");

  const handleSelectFolder = async () => {
    if (!isDesktop) return;
    try {
      const selected = await openDialog({
        directory: true,
        multiple: false,
        title: "Select Export Directory"
      });
      if (selected && typeof selected === "string") {
        setExportPath(selected);
      }
    } catch (err) {
      console.error("Failed to open dialog", err);
    }
  };

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [draftText, setDraftText] = useState("");
  const [showUnsavedWarning, setShowUnsavedWarning] = useState<{
    action: "start" | "switch" | "close";
    targetId?: string;
  } | null>(null);
  const isExecutingRef = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      setLocalFiles((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  useEffect(() => {
    if (isOpen && files.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocalFiles([...files]);
      setSelectedIds(new Set(files.map((f) => f.id)));
      setIsSubmitting(false);
      setActivePreviewId(files[0].id);
      setIsEditing(false);
      setDraftText("");
      setShowUnsavedWarning(null);
    }
  }, [isOpen, files]);

  if (!isOpen) return null;

  const handleToggleAll = () => {
    if (selectedIds.size === localFiles.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(localFiles.map((f) => f.id)));
    }
  };

  const handleToggle = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  const startEdit = () => {
    const file = localFiles.find((f) => f.id === activePreviewId);
    if (file) {
      setDraftText(file.text);
      setIsEditing(true);
    }
  };

  const saveEdit = () => {
    setLocalFiles((prev) =>
      prev.map((f) => {
        if (f.id === activePreviewId) {
          return { ...f, text: draftText, characterCount: draftText.length };
        }
        return f;
      }),
    );
    setIsEditing(false);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setDraftText("");
  };

  const updateFileSpeed = (id: string, speed: number) => {
    setLocalFiles((prev) =>
      prev.map((f) => {
        if (f.id === id) {
          return { ...f, speed };
        }
        return f;
      }),
    );
  };

  const requestSwitchFile = (id: string) => {
    if (
      isEditing &&
      draftText !== localFiles.find((f) => f.id === activePreviewId)?.text
    ) {
      setShowUnsavedWarning({ action: "switch", targetId: id });
    } else {
      setIsEditing(false);
      setActivePreviewId(id);
    }
  };

  const requestStart = () => {
    if (
      isEditing &&
      draftText !== localFiles.find((f) => f.id === activePreviewId)?.text
    ) {
      setShowUnsavedWarning({ action: "start" });
    } else {
      executeStart();
    }
  };

  const requestClose = () => {
    // User requested "còn case close thì close luôn", no warning
    onClose();
  };

  const handleWarningConfirm = () => {
    if (!showUnsavedWarning) return;

    // Force save
    saveEdit();

    if (showUnsavedWarning.action === "start") {
      // Must wait for state to settle, but we can do it directly with updated files
      executeStart(draftText);
    } else if (
      showUnsavedWarning.action === "switch" &&
      showUnsavedWarning.targetId
    ) {
      setActivePreviewId(showUnsavedWarning.targetId);
      setIsEditing(false);
    }

    setShowUnsavedWarning(null);
  };

  const handleWarningDiscard = () => {
    // Just close the warning and stay on the current file
    setShowUnsavedWarning(null);
  };

  const executeStart = async (overrideDraftText?: string) => {
    if (isExecutingRef.current) return;
    isExecutingRef.current = true;
    setIsSubmitting(true);

    // If we have an override, we need to map it since state update might not have applied yet
    const finalFiles = localFiles.map((f) => {
      if (overrideDraftText && f.id === activePreviewId) {
        return {
          ...f,
          text: overrideDraftText,
          characterCount: overrideDraftText.length,
        };
      }
      return f;
    });

    const selectedFiles = finalFiles.filter((f) => selectedIds.has(f.id));
    await onStartJobs(selectedFiles, exportPath, exportFormat);

    setIsSubmitting(false);
    isExecutingRef.current = false;
    onClose();
  };

  const activeFile = localFiles.find((f) => f.id === activePreviewId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-6xl h-[85vh] bg-card border border-border shadow-2xl rounded-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 relative">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border/50 bg-muted/30 shrink-0">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-bold tracking-tight">
              {t("generate.batchModalTitle")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("generate.batchModalDesc")}
            </p>
          </div>
          <button
            onClick={requestClose}
            disabled={isSubmitting}
            className="p-2 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 2-Column Layout */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Left Column: File List */}
          <div className="w-1/3 min-w-[320px] max-w-[450px] flex flex-col border-r border-border/50 bg-background">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/30 bg-muted/10 shrink-0">
              <button
                onClick={handleToggleAll}
                className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                {selectedIds.size === localFiles.length ? (
                  <CheckSquare className="w-4 h-4 text-primary" />
                ) : (
                  <Square className="w-4 h-4 text-muted-foreground" />
                )}
                {selectedIds.size === localFiles.length
                  ? t("generate.batchDeselectAll")
                  : t("generate.batchSelectAll")}
              </button>
              <div className="text-xs font-medium text-muted-foreground bg-muted px-2 py-1 rounded-md">
                <span className="text-foreground">{selectedIds.size}</span> /{" "}
                {localFiles.length}
              </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2 relative">
              <DndContext 
                sensors={sensors}
                collisionDetection={closestCenter}
                modifiers={[restrictToVerticalAxis, restrictToParentElement]}
                onDragEnd={handleDragEnd}
              >
                <SortableContext 
                  items={localFiles.map(f => f.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {localFiles.map((file) => (
                    <SortableFileItem 
                      key={file.id}
                      file={file}
                      isSelected={selectedIds.has(file.id)}
                      isActive={activePreviewId === file.id}
                      onToggle={handleToggle}
                      onSelect={requestSwitchFile}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            </div>
          </div>

          {/* Right Column: Text Preview */}
          <div className="flex-1 flex flex-col bg-muted/10 min-w-0 relative">
            {activeFile ? (
              <>
                {/* Preview Header */}
                <div className="flex items-center justify-between gap-3 px-6 py-4 border-b border-border/50 bg-background/50 backdrop-blur-sm shrink-0">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 text-primary">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0 flex flex-col gap-1">
                      <h3 className="text-sm font-bold truncate text-foreground">
                        {activeFile.fileName}
                      </h3>
                      <div className="flex items-center gap-3">
                        <p className="text-xs text-muted-foreground">
                          {isEditing
                            ? draftText.length
                            : activeFile.characterCount.toLocaleString()}{" "}
                          {isVi ? "ký tự" : "characters"}
                        </p>
                        <div className="flex items-center gap-2 border-l border-border/50 pl-4">
                           <div className="flex items-center gap-1.5 px-2 py-1 bg-orange-500/10 border border-orange-500/20 rounded-md text-orange-600 dark:text-orange-400">
                             <Zap className="w-3.5 h-3.5" />
                             <span className="text-[10px] font-bold uppercase tracking-wider">{t("generate.speed")}</span>
                           </div>
                           <select 
                             className="text-sm bg-muted/50 border border-border/50 rounded-md px-2 py-1 font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-orange-500/50 hover:bg-muted transition-colors cursor-pointer"
                             value={activeFile.speed || 1.0}
                             onChange={(e) => updateFileSpeed(activeFile.id, parseFloat(e.target.value))}
                           >
                             {[0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0].map(s => (
                               <option key={s} value={s}>{s.toFixed(2)}x</option>
                             ))}
                           </select>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isEditing ? (
                      <>
                        <button
                          onClick={cancelEdit}
                          className="text-xs font-medium px-3 py-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                        >
                          {t("common.cancel")}
                        </button>
                        <button
                          onClick={saveEdit}
                          className="text-xs font-medium px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:brightness-110 transition-all shadow-sm"
                        >
                          {t("common.save")}
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={startEdit}
                        className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 text-foreground transition-colors border border-border/50"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        {isVi ? "Sửa văn bản" : "Edit Text"}
                      </button>
                    )}
                  </div>
                </div>
                {/* Preview Content */}
                <div className="flex-1 overflow-hidden p-6 relative">
                  {isEditing ? (
                    <textarea
                      value={draftText}
                      onChange={(e) => setDraftText(e.target.value)}
                      className="w-full h-full p-6 rounded-2xl bg-card border-2 border-primary/50 shadow-sm text-sm leading-relaxed text-foreground font-sans resize-none focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all custom-scrollbar"
                      placeholder={isVi ? "Nhập hoặc dán văn bản tại đây…" : "Type or paste text here..."}
                      spellCheck={false}
                    />
                  ) : (
                    <div className="w-full h-full p-6 rounded-2xl bg-card border border-border shadow-sm overflow-y-auto custom-scrollbar">
                      <pre className="text-sm leading-relaxed text-foreground whitespace-pre-wrap font-sans">
                        {activeFile.text}
                      </pre>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <Eye className="w-12 h-12 mb-4 opacity-20" />
                <p className="font-medium">{isVi ? "Chọn một file để xem trước hoặc chỉnh sửa" : "Select a file to preview or edit"}</p>
              </div>
            )}
          </div>
          
          {/* Export Settings */}
          <div className="shrink-0 p-6 border-t border-border/50 bg-muted/10">
            <h4 className="text-sm font-bold text-foreground mb-3 flex items-center gap-2">
              <FolderOutput className="w-4 h-4 text-primary" />
              {isVi ? "Tự động xuất file (Tùy chọn)" : "Auto-Export (Optional)"}
            </h4>
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground w-16">{isVi ? "Định dạng:" : "Format:"}</span>
                <div className="flex bg-muted rounded-lg p-1">
                  <button
                    onClick={() => setExportFormat("mp3")}
                    className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${
                      exportFormat === "mp3"
                        ? "bg-background text-foreground shadow-sm ring-1 ring-border"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    MP3
                  </button>
                  <button
                    onClick={() => setExportFormat("m4a")}
                    className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${
                      exportFormat === "m4a"
                        ? "bg-background text-foreground shadow-sm ring-1 ring-border"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    M4A
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground w-16">{isVi ? "Thư mục:" : "Folder:"}</span>
                {isDesktop ? (
                  <div className="flex-1 flex gap-2">
                    <input
                      type="text"
                      readOnly
                      value={exportPath || ""}
                      placeholder={isVi ? "Chọn thư mục lưu file…" : "Select output directory..."}
                      className="flex-1 bg-background border border-border rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                    <button
                      onClick={handleSelectFolder}
                      className="px-4 py-2 bg-secondary text-secondary-foreground rounded-xl text-sm font-bold hover:brightness-110 transition-all border border-border/50"
                    >
                      {isVi ? "Duyệt" : "Browse"}
                    </button>
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground italic">
                    {isVi ? "Tự động xuất file chỉ khả dụng trên ứng dụng Desktop." : "Auto-export is only available in the desktop app."}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border/50 bg-background flex items-center justify-between shrink-0">
          <div className="text-sm text-muted-foreground">
            {isVi ? "Sẵn sàng tạo " : "Ready to process "}
            <span className="font-bold text-foreground">
              {selectedIds.size}
            </span>{" "}
            {isVi ? "file" : `file${selectedIds.size !== 1 ? "s" : ""}`}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={requestClose}
              disabled={isSubmitting}
              className="px-6 py-2.5 rounded-xl text-sm font-bold text-foreground hover:bg-muted transition-colors border border-transparent disabled:opacity-50"
            >
              {t("common.cancel")}
            </button>
            <button
              onClick={requestStart}
              disabled={isSubmitting || selectedIds.size === 0}
              className="flex items-center gap-2 px-8 py-2.5 rounded-xl text-sm font-bold bg-primary text-primary-foreground hover:brightness-110 active:scale-[0.98] transition-all shadow-md shadow-primary/20 disabled:opacity-50 disabled:pointer-events-none"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {isVi ? `Bắt đầu ${selectedIds.size} tác vụ` : `Start ${selectedIds.size} Jobs`}
            </button>
          </div>
        </div>

        {/* Warning Dialog Overlay */}
        {showUnsavedWarning && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="w-full max-w-sm bg-card border border-border shadow-2xl rounded-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
              <div className="p-6">
                <h3 className="text-lg font-bold mb-3 text-foreground">{isVi ? "Thay đổi chưa được lưu" : "Unsaved Changes"}</h3>
                <p className="text-sm text-muted-foreground mb-2">
                  {isVi ? "Bạn có thay đổi chưa lưu trong file sau:" : "You have unsaved edits in the following file:"}
                </p>
                <div className="p-2 mb-3 bg-muted/50 rounded-lg border border-border/50 text-sm font-bold text-foreground truncate" title={activeFile?.fileName}>
                  {activeFile?.fileName}
                </div>
                <p className="text-sm text-muted-foreground">
                  {isVi ? "Bạn có muốn lưu trước khi tiếp tục không?" : "Do you want to save them before continuing?"}
                </p>
              </div>
              <div className="flex items-center gap-2 p-4 border-t border-border/50 bg-muted/20">
                <button
                  onClick={handleWarningDiscard}
                  className="flex-1 px-4 py-2 rounded-xl text-sm font-bold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  {isVi ? "Quay lại" : "Go Back"}
                </button>
                <button
                  onClick={handleWarningConfirm}
                  className="flex-1 px-4 py-2 rounded-xl text-sm font-bold bg-primary text-primary-foreground hover:brightness-110 transition-all shadow-sm"
                >
                  {isVi ? "Lưu & Tiếp tục" : "Save & Continue"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
