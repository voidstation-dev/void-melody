import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { useLocation } from "@tanstack/react-router"

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMounted(true)
  }, [])

  // Hide on settings page because settings page already has appearance controls
  if (location.pathname === "/settings") {
    return null
  }

  if (!mounted) {
    return <div className="h-9 w-9 rounded-xl border border-border/40 bg-muted/20" />
  }

  const isDark = resolvedTheme === "dark"

  const toggleTheme = () => {
    setTheme(isDark ? "light" : "dark")
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border/70 bg-card hover:bg-muted text-foreground transition-all duration-200 shadow-2xs hover:shadow-xs active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer ${className || ""}`}
      title={isDark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
      aria-label="Toggle theme"
    >
      {isDark ? (
        <Sun className="h-4 w-4 text-amber-400 transition-transform duration-300 rotate-0 hover:rotate-45" />
      ) : (
        <Moon className="h-4 w-4 text-slate-700 dark:text-slate-200 transition-transform duration-300 rotate-0 hover:-rotate-12" />
      )}
    </button>
  )
}
