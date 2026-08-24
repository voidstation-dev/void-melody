import { Sparkles, Smile } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { EmotionTag } from "./emotion-tag"
import { NATIVE_CUES, EMOTION_TAGS } from "../lib/delivery-tags"

interface EmotionPanelProps {
  onInsertTag: (token: string) => void
}

export function EmotionPanel({ onInsertTag }: EmotionPanelProps) {
  return (
    <Card className="border-border/80 shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <Smile className="h-3.5 w-3.5" />
          </div>
          <CardTitle className="text-sm font-bold">Ngữ điệu & Cảm xúc</CardTitle>
        </div>
        <CardDescription className="text-xs">
          Thêm cách thể hiện cho toàn bài hoặc chèn vào từng đoạn tại vị trí con trỏ.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Native Cues */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
            <Sparkles className="h-3 w-3" />
            <span>Âm thanh tự nhiên (Native Cue)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {NATIVE_CUES.map((tag) => (
              <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
            ))}
          </div>
        </div>

        {/* Emotion Intents */}
        <div className="space-y-2">
          <div className="text-[11px] font-extrabold uppercase tracking-wider text-amber-600 dark:text-amber-400">
            Cảm xúc & Sắc thái kịch bản
          </div>
          <div className="flex flex-wrap gap-2">
            {EMOTION_TAGS.map((tag) => (
              <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
