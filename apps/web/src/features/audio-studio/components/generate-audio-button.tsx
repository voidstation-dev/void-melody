import { Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTranslation } from "@/hooks/use-translation"

interface GenerateAudioButtonProps {
  onClick: () => void
  disabled?: boolean
  isLoading?: boolean
}

export function GenerateAudioButton({
  onClick,
  disabled,
  isLoading,
}: GenerateAudioButtonProps) {
  const { t } = useTranslation()

  return (
    <Button
      type="button"
      size="lg"
      onClick={onClick}
      disabled={disabled || isLoading}
      className="w-full h-12 rounded-2xl gap-2 text-sm font-extrabold shadow-md transition-all active:scale-[0.98] cursor-pointer"
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>{t("audioStudio.generatingBtn")}</span>
        </>
      ) : (
        <>
          <Sparkles className="h-4 w-4" />
          <span>{t("audioStudio.generateBtn")}</span>
          <span className="ml-auto rounded-md bg-primary-foreground/20 px-1.5 py-0.5 text-[10px] font-mono font-normal">
            {t("audioStudio.shortcutHint")}
          </span>
        </>
      )}
    </Button>
  )
}
