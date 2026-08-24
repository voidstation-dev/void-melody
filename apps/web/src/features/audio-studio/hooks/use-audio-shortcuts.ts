import { useEffect } from "react"

type ShortcutsConfig = {
  onGenerate?: () => void
  onSaveDraft?: () => void
  disabled?: boolean
}

export function useAudioShortcuts({ onGenerate, onSaveDraft, disabled }: ShortcutsConfig) {
  useEffect(() => {
    if (disabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl + Enter or Cmd + Enter -> Generate Audio
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault()
        onGenerate?.()
      }

      // Ctrl + S or Cmd + S -> Save Draft
      if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
        e.preventDefault()
        onSaveDraft?.()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onGenerate, onSaveDraft, disabled])
}
