import { useState } from "react"
import { Sliders, ChevronDown, ChevronUp } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { EmotionTag } from "./emotion-tag"
import { ADVANCED_DELIVERY_TAGS } from "../lib/delivery-tags"

interface DeliveryPanelProps {
  onInsertTag: (token: string) => void
}

export function DeliveryPanel({ onInsertTag }: DeliveryPanelProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Card className="border-border/80 shadow-sm overflow-hidden">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center justify-between p-4 sm:p-5 text-left transition-colors hover:bg-muted/40 cursor-pointer select-none"
          >
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400">
                <Sliders className="h-3.5 w-3.5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-foreground">Ngữ điệu nâng cao</h3>
                <p className="text-xs text-muted-foreground">Điều chỉnh tốc độ, độ ngắt nghỉ và sắc thái từng câu</p>
              </div>
            </div>
            <div className="rounded-lg p-1 text-muted-foreground transition-transform">
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="pt-0 pb-5">
            <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40">
              {ADVANCED_DELIVERY_TAGS.map((tag) => (
                <EmotionTag key={tag.id} tag={tag} onClick={onInsertTag} />
              ))}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
