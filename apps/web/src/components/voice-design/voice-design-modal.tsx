import * as React from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { useTranslation } from "@/hooks/use-translation"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2, Sparkles, Check, Play } from "lucide-react"
import { createVoiceDesignPreviews, commitVoiceDesign, resolveCandidateAudioUrl } from "@/api/voice-design"
import type { VoiceDesignCandidate } from "@/types/voice-design"

type Step = "describe" | "preview"

export function VoiceDesignModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [step, setStep] = React.useState<Step>("describe")
  const [prompt, setPrompt] = React.useState("")
  const [previewText, setPreviewText] = React.useState("Xin chào, đây là giọng nói mẫu của tôi.")
  const [language, setLanguage] = React.useState("vi-VN")
  const [count, setCount] = React.useState(3)
  const [sessionId, setSessionId] = React.useState<string | null>(null)
  const [candidates, setCandidates] = React.useState<VoiceDesignCandidate[]>([])
  const [selectedCandidate, setSelectedCandidate] = React.useState<string | null>(null)
  const [displayName, setDisplayName] = React.useState("")
  const [playingId, setPlayingId] = React.useState<string | null>(null)
  const [committedVoiceId, setCommittedVoiceId] = React.useState<string | null>(null)

  const audioRef = React.useRef<HTMLAudioElement | null>(null)

  const previewMutation = useMutation({
    mutationFn: createVoiceDesignPreviews,
    onSuccess: (data) => {
      setSessionId(data.sessionId)
      setCandidates(data.candidates)
      setStep("preview")
    },
  })

  const commitMutation = useMutation({
    mutationFn: ({ sessionId, candidateId, displayName }: { sessionId: string; candidateId: string; displayName: string }) =>
      commitVoiceDesign(sessionId, { candidateId, displayName }),
    onSuccess: (data) => {
      setCommittedVoiceId(data.voiceId)
      queryClient.invalidateQueries({ queryKey: ["custom-voices"] })
    },
  })

  const isBusy = previewMutation.isPending || commitMutation.isPending

  const stopPlayback = React.useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ""
      audioRef.current = null
    }
    setPlayingId(null)
  }, [])

  function handlePlay(candidateId: string, audioUrl: string) {
    if (playingId === candidateId) {
      stopPlayback()
      return
    }
    stopPlayback()
    const audio = new Audio(resolveCandidateAudioUrl(audioUrl))
    audio.onended = () => setPlayingId(null)
    audio.onerror = () => setPlayingId(null)
    audio.play().catch(() => setPlayingId(null))
    audioRef.current = audio
    setPlayingId(candidateId)
  }

  function handleGenerate() {
    if (!prompt.trim()) return
    previewMutation.mutate({
      prompt,
      previewText,
      language,
      count,
    })
  }

  function handleCommit() {
    if (!sessionId || !selectedCandidate || !displayName.trim()) return
    commitMutation.mutate({ sessionId, candidateId: selectedCandidate, displayName: displayName.trim() })
  }

  if (!open) return null

  return (
    <Dialog open={open} onOpenChange={(value) => !isBusy && !value && onClose()}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!isBusy}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-500" />
            {t("voiceLab.designTitle")}
          </DialogTitle>
          <DialogDescription>{t("voiceLab.designSubtitle")}</DialogDescription>
        </DialogHeader>

        {step === "describe" && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground">{t("voiceLab.designPromptLabel")}</label>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={t("voiceLab.designPromptPlaceholder")}
                rows={4}
              />
              <p className="text-[11px] text-muted-foreground">{t("voiceLab.designPromptHint")}</p>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-foreground">{t("voiceLab.designPreviewTextLabel")}</label>
              <Input value={previewText} onChange={(e) => setPreviewText(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground">{t("voiceLab.languageLabel")}</label>
                <Input value={language} onChange={(e) => setLanguage(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground">{t("voiceLab.designPreviewCountLabel")}</label>
                <div className="flex items-center gap-1">
                  {[1, 2, 3].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setCount(n)}
                      className={`h-8 flex-1 rounded-lg text-xs font-bold border ${count === n ? "bg-primary text-primary-foreground border-primary" : "bg-card border-border text-muted-foreground hover:bg-muted"}`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {step === "preview" && (
          <div className="space-y-4">
            {previewMutation.isPending ? (
              <div className="py-10 text-center">
                <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary" />
                <p className="mt-3 text-sm font-medium">{t("voiceLab.designGeneratingPreview")}</p>
              </div>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">
                  {t("voiceLab.designPreviewInstructionLabel")}: <span className="font-semibold text-foreground">{previewMutation.data?.compiledInstruction}</span>
                </p>
                <div className="grid gap-2.5">
                  {candidates.map((candidate) => (
                    <button
                      key={candidate.id}
                      type="button"
                      onClick={() => setSelectedCandidate(candidate.id)}
                      className={`flex items-center gap-3 rounded-xl border p-3 text-left transition-colors ${selectedCandidate === candidate.id ? "border-primary bg-primary/5" : "border-border bg-card hover:bg-muted/40"}`}
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                        <Play className="h-4 w-4 text-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-bold">{t("voiceLab.designCandidateLabel", { index: candidates.indexOf(candidate) + 1 })}</p>
                        <p className="text-[11px] text-muted-foreground truncate">{t("voiceLab.designCandidateHint")}</p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handlePlay(candidate.id, candidate.audioUrl)
                        }}
                        className="shrink-0 rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary hover:bg-primary hover:text-primary-foreground"
                      >
                        {playingId === candidate.id ? t("common.pause") : t("common.play")}
                      </button>
                      {selectedCandidate === candidate.id && <Check className="h-4 w-4 text-primary" />}
                    </button>
                  ))}
                </div>
                {selectedCandidate && (
                  <div className="space-y-1.5 pt-1">
                    <label className="text-xs font-bold text-foreground">{t("voiceLab.designVoiceNameLabel")}</label>
                    <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder={t("voiceLab.designVoiceNamePlaceholder")} />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {committedVoiceId && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm">
            <p className="font-bold text-emerald-700 dark:text-emerald-400">{t("voiceLab.designSaved")}</p>
            <p className="text-[11px] text-emerald-700/80 dark:text-emerald-400/80">{t("voiceLab.designSavedHint")}</p>
          </div>
        )}

        <DialogFooter>
          {step === "describe" ? (
            <Button disabled={!prompt.trim() || previewMutation.isPending} onClick={handleGenerate}>
              {previewMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {t("voiceLab.designGeneratePreview")}
            </Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => setStep("describe")} disabled={commitMutation.isPending || !!committedVoiceId}>
                {t("common.back")}
              </Button>
              <Button disabled={!selectedCandidate || !displayName.trim() || commitMutation.isPending || !!committedVoiceId} onClick={handleCommit}>
                {commitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {t("common.save")}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
