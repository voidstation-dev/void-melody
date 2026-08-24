import { useState } from "react"
import { Check, ChevronsUpDown, Mic, Sparkles, UserCheck, Play, Pause, Loader2 } from "lucide-react"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useVoicePreview } from "@/hooks/use-voice-preview"
import { cn } from "@/lib/utils"

interface VoiceItem {
  id?: string
  voiceType: string
  displayName: string
  languageCode?: string
  providerId?: string
  resourceId?: string
}

interface VoiceSelectorProps {
  selectedVoiceId: string
  onSelectVoice: (voiceId: string) => void
  voices: VoiceItem[]
  disabled?: boolean
}

export function VoiceSelector({
  selectedVoiceId,
  onSelectVoice,
  voices,
  disabled,
}: VoiceSelectorProps) {
  const [open, setOpen] = useState(false)
  const { isPlaying, activeVoiceType, togglePreview } = useVoicePreview()

  const currentVoice = voices.find(
    (v) => v.voiceType === selectedVoiceId || v.id === selectedVoiceId,
  )

  const isVieNeu = currentVoice?.providerId === "vieneu" || selectedVoiceId.toLowerCase().includes("vieneu")
  const isCustom = currentVoice?.providerId === "custom"

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
          <Mic className="h-3.5 w-3.5 text-muted-foreground" />
          <span>Giọng đọc</span>
        </label>
        {currentVoice && (
          <span className="text-[11px] font-semibold text-muted-foreground">
            {currentVoice.languageCode || "vi-VN"}
          </span>
        )}
      </div>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            disabled={disabled}
            className={cn(
              "flex w-full items-center justify-between rounded-2xl border border-border bg-card p-3 text-left transition-all hover:bg-muted/40 hover:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer shadow-xs disabled:opacity-50 disabled:pointer-events-none",
              open && "border-primary ring-2 ring-primary/20",
            )}
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-bold text-xs transition-colors",
                  isVieNeu
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : isCustom
                      ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                      : "bg-muted text-muted-foreground border border-border/40",
                )}
              >
                {isVieNeu ? (
                  <Sparkles className="h-4 w-4" />
                ) : isCustom ? (
                  <UserCheck className="h-4 w-4" />
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </div>
              <div className="truncate">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-foreground truncate">
                    {currentVoice?.displayName || selectedVoiceId || "Chọn giọng đọc…"}
                  </span>
                  {isVieNeu && (
                    <Badge variant="secondary" className="bg-primary/10 text-primary text-[10px] font-bold px-1.5 py-0">
                      VieNeu
                    </Badge>
                  )}
                  {isCustom && (
                    <Badge variant="secondary" className="bg-amber-500/10 text-amber-600 text-[10px] font-bold px-1.5 py-0">
                      Đã nhân bản
                    </Badge>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                  {isVieNeu
                    ? "Neural TTS · Hỗ trợ toàn bộ cảm xúc & Native Cues"
                    : isCustom
                      ? "Giọng nhân bản tùy chỉnh"
                      : "Streaming TTS tiêu chuẩn"}
                </p>
              </div>
            </div>

            <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground ml-2" />
          </button>
        </PopoverTrigger>

        <PopoverContent className="w-[340px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Tìm kiếm giọng đọc theo tên…" className="h-10 text-xs" />
            <CommandList className="max-h-[300px]">
              <CommandEmpty>Không tìm thấy giọng đọc phù hợp.</CommandEmpty>

              <CommandGroup heading="VieNeu Studio (Khuyên dùng)">
                {voices
                  .filter((v) => v.providerId === "vieneu" || (!v.providerId && v.voiceType.includes("vieneu")))
                  .map((v) => {
                    const isSelected = v.voiceType === selectedVoiceId || v.id === selectedVoiceId
                    const playing = isPlaying && activeVoiceType === v.voiceType

                    return (
                      <CommandItem
                        key={v.voiceType}
                        value={`${v.displayName} ${v.voiceType}`}
                        onSelect={() => {
                          onSelectVoice(v.voiceType)
                          setOpen(false)
                        }}
                        className="flex items-center justify-between py-2 px-2.5 rounded-xl cursor-pointer"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <Check
                            className={cn(
                              "h-4 w-4 shrink-0 text-primary",
                              isSelected ? "opacity-100" : "opacity-0",
                            )}
                          />
                          <div className="truncate">
                            <p className="font-bold text-xs text-foreground truncate">{v.displayName}</p>
                            <p className="text-[10px] text-muted-foreground truncate">{v.languageCode || "vi-VN"}</p>
                          </div>
                        </div>

                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            togglePreview(v.voiceType)
                          }}
                          className="h-7 w-7 p-0 rounded-lg shrink-0 text-muted-foreground hover:text-primary"
                        >
                          {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                        </Button>
                      </CommandItem>
                    )
                  })}
              </CommandGroup>

              {voices.some((v) => v.providerId === "custom") && (
                <CommandGroup heading="Giọng đã nhân bản (Custom Clones)">
                  {voices
                    .filter((v) => v.providerId === "custom")
                    .map((v) => {
                      const isSelected = v.voiceType === selectedVoiceId || v.id === selectedVoiceId
                      return (
                        <CommandItem
                          key={v.id || v.voiceType}
                          value={`${v.displayName} ${v.voiceType}`}
                          onSelect={() => {
                            onSelectVoice(v.voiceType)
                            setOpen(false)
                          }}
                          className="flex items-center justify-between py-2 px-2.5 rounded-xl cursor-pointer"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <Check
                              className={cn(
                                "h-4 w-4 shrink-0 text-primary",
                                isSelected ? "opacity-100" : "opacity-0",
                              )}
                            />
                            <div className="truncate">
                              <p className="font-bold text-xs text-foreground truncate">{v.displayName}</p>
                              <p className="text-[10px] text-amber-600 font-semibold truncate">Giọng nhân bản</p>
                            </div>
                          </div>
                        </CommandItem>
                      )
                    })}
                </CommandGroup>
              )}

              {voices.some((v) => v.providerId !== "vieneu" && v.providerId !== "custom" && !v.voiceType.includes("vieneu")) && (
                <CommandGroup heading="Giọng đọc khác (CapCut / Streaming)">
                  {voices
                    .filter((v) => v.providerId !== "vieneu" && v.providerId !== "custom" && !v.voiceType.includes("vieneu"))
                    .map((v) => {
                      const isSelected = v.voiceType === selectedVoiceId || v.id === selectedVoiceId
                      const playing = isPlaying && activeVoiceType === v.voiceType

                      return (
                        <CommandItem
                          key={v.voiceType}
                          value={`${v.displayName} ${v.voiceType}`}
                          onSelect={() => {
                            onSelectVoice(v.voiceType)
                            setOpen(false)
                          }}
                          className="flex items-center justify-between py-2 px-2.5 rounded-xl cursor-pointer"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <Check
                              className={cn(
                                "h-4 w-4 shrink-0 text-primary",
                                isSelected ? "opacity-100" : "opacity-0",
                              )}
                            />
                            <div className="truncate">
                              <p className="font-bold text-xs text-foreground truncate">{v.displayName}</p>
                              <p className="text-[10px] text-muted-foreground truncate">{v.languageCode || "vi-VN"}</p>
                            </div>
                          </div>

                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              togglePreview(v.voiceType)
                            }}
                            className="h-7 w-7 p-0 rounded-lg shrink-0 text-muted-foreground hover:text-primary"
                          >
                            {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                          </Button>
                        </CommandItem>
                      )
                    })}
                </CommandGroup>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  )
}
