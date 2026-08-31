import React, { createContext, useContext, useEffect, useMemo, useState } from "react"
import { useTheme } from "next-themes"
import { THEME_PRESETS, getThemeById } from "@/lib/themes/theme-presets"
import type { ThemePreset, ThemeStyles } from "@/lib/themes/theme-types"

const THEME_STORAGE_KEY = "voidmelody_theme_palette_id_v1"
const RADIUS_STORAGE_KEY = "voidmelody_theme_radius_v1"

interface ThemePaletteContextType {
  activeThemeId: string
  activeTheme: ThemePreset
  setThemeId: (id: string) => void
  radius: number
  setRadius: (radius: number) => void
  shuffleTheme: () => void
  allThemes: ThemePreset[]
}

const ThemePaletteContext = createContext<ThemePaletteContextType | null>(null)

function applyThemeStyles(styles: ThemeStyles, radius: number) {
  if (typeof document === "undefined") return
  const root = document.documentElement

  const styleMapping: Record<string, string> = {
    background: styles.background,
    foreground: styles.foreground,
    card: styles.card,
    "card-foreground": styles.cardForeground,
    popover: styles.popover,
    "popover-foreground": styles.popoverForeground,
    primary: styles.primary,
    "primary-foreground": styles.primaryForeground,
    secondary: styles.secondary,
    "secondary-foreground": styles.secondaryForeground,
    muted: styles.muted,
    "muted-foreground": styles.mutedForeground,
    accent: styles.accent,
    "accent-foreground": styles.accentForeground,
    destructive: styles.destructive,
    "destructive-foreground": styles.destructiveForeground,
    border: styles.border,
    input: styles.input,
    ring: styles.ring,
  }

  if (styles.sidebar) styleMapping.sidebar = styles.sidebar
  if (styles.sidebarForeground) styleMapping["sidebar-foreground"] = styles.sidebarForeground
  if (styles.sidebarPrimary) styleMapping["sidebar-primary"] = styles.sidebarPrimary
  if (styles.sidebarPrimaryForeground) styleMapping["sidebar-primary-foreground"] = styles.sidebarPrimaryForeground
  if (styles.sidebarAccent) styleMapping["sidebar-accent"] = styles.sidebarAccent
  if (styles.sidebarAccentForeground) styleMapping["sidebar-accent-foreground"] = styles.sidebarAccentForeground
  if (styles.sidebarBorder) styleMapping["sidebar-border"] = styles.sidebarBorder
  if (styles.sidebarRing) styleMapping["sidebar-ring"] = styles.sidebarRing

  for (const [varName, value] of Object.entries(styleMapping)) {
    root.style.setProperty(`--${varName}`, value)
  }

  root.style.setProperty("--radius", `${radius}rem`)
}

export function ThemePaletteProvider({ children }: { children: React.ReactNode }) {
  const { resolvedTheme, theme } = useTheme()

  const [activeThemeId, setActiveThemeIdState] = useState<string>(() => {
    if (typeof window === "undefined") return "default"
    return localStorage.getItem(THEME_STORAGE_KEY) || "default"
  })

  const [radius, setRadiusState] = useState<number>(() => {
    if (typeof window === "undefined") return 0.75
    const stored = localStorage.getItem(RADIUS_STORAGE_KEY)
    return stored ? parseFloat(stored) : 0.75
  })

  const activeTheme = useMemo(() => getThemeById(activeThemeId), [activeThemeId])

  const setThemeId = (id: string) => {
    setActiveThemeIdState(id)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, id)
    } catch {
      // ignore
    }
  }

  const setRadius = (newRadius: number) => {
    setRadiusState(newRadius)
    try {
      localStorage.setItem(RADIUS_STORAGE_KEY, newRadius.toString())
    } catch {
      // ignore
    }
  }

  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const shuffleTheme = () => {
    const others = THEME_PRESETS.filter((t) => t.id !== activeThemeId)
    const random = others[Math.floor(Math.random() * others.length)]
    if (random) {
      setThemeId(random.id)
    }
  }

  // Update styles when active theme, resolved theme mode, or radius changes
  useEffect(() => {
    if (!mounted) return

    let isDark = resolvedTheme === "dark"
    if (!resolvedTheme) {
      isDark =
        theme === "dark" ||
        (theme === "system" &&
          typeof window !== "undefined" &&
          window.matchMedia("(prefers-color-scheme: dark)").matches)
    }

    const styles = isDark ? activeTheme.dark : activeTheme.light
    applyThemeStyles(styles, radius)
  }, [activeTheme, resolvedTheme, theme, radius, mounted])

  // Listen to class changes on document.documentElement (added/removed by next-themes)
  useEffect(() => {
    if (typeof document === "undefined") return

    const root = document.documentElement
    const observer = new MutationObserver(() => {
      const isDarkNow = root.classList.contains("dark")
      const styles = isDarkNow ? activeTheme.dark : activeTheme.light
      applyThemeStyles(styles, radius)
    })

    observer.observe(root, {
      attributes: true,
      attributeFilter: ["class"],
    })

    return () => observer.disconnect()
  }, [activeTheme, radius])

  return (
    <ThemePaletteContext.Provider
      value={{
        activeThemeId,
        activeTheme,
        setThemeId,
        radius,
        setRadius,
        shuffleTheme,
        allThemes: THEME_PRESETS,
      }}
    >
      {children}
    </ThemePaletteContext.Provider>
  )
}

export function useThemePalette() {
  const context = useContext(ThemePaletteContext)
  if (!context) {
    throw new Error("useThemePalette must be used within a ThemePaletteProvider")
  }
  return context
}
