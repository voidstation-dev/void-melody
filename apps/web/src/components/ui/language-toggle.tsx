import { Globe } from "lucide-react"
import { useTranslation } from "@/hooks/use-translation"
import { useLocation } from "@tanstack/react-router"
import { useEffect, useState } from "react"

export function LanguageToggle({ className }: { className?: string }) {
  const { locale, setLocale, isVi } = useTranslation()
  const [mounted, setMounted] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMounted(true)
  }, [])

  // Hide on settings page because settings page already has language controls
  if (location.pathname === "/settings") {
    return null
  }

  if (!mounted) {
    return <div className="h-9 w-14 rounded-xl border border-border/40 bg-muted/20" />
  }

  const toggleLanguage = () => {
    setLocale(isVi ? "en" : "vi")
  }

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      className={`inline-flex h-9 items-center gap-1.5 rounded-xl border border-border/70 bg-card px-2.5 text-xs font-bold text-foreground hover:bg-muted transition-all duration-200 shadow-2xs hover:shadow-xs active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer ${className || ""}`}
      title={isVi ? "Chuyển sang Tiếng Anh (English)" : "Switch to Vietnamese (Tiếng Việt)"}
      aria-label="Toggle language"
    >
      <Globe className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="font-mono uppercase text-[11px] font-extrabold tracking-wider text-primary">
        {locale}
      </span>
    </button>
  )
}
