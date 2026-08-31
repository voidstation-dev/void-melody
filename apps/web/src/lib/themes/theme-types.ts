export type ThemeCategory =
  | "all"
  | "studio"
  | "cyber"
  | "nature"
  | "pastel"
  | "classic"

export interface ThemeStyles {
  background: string
  foreground: string
  card: string
  cardForeground: string
  popover: string
  popoverForeground: string
  primary: string
  primaryForeground: string
  secondary: string
  secondaryForeground: string
  muted: string
  mutedForeground: string
  accent: string
  accentForeground: string
  destructive: string
  destructiveForeground: string
  border: string
  input: string
  ring: string
  sidebar?: string
  sidebarForeground?: string
  sidebarPrimary?: string
  sidebarPrimaryForeground?: string
  sidebarAccent?: string
  sidebarAccentForeground?: string
  sidebarBorder?: string
  sidebarRing?: string
}

export interface ThemePreset {
  id: string
  name: string
  category: ThemeCategory
  descriptionVi: string
  descriptionEn: string
  /**
   * 4-color swatch preview: [primary, secondary, accent, background]
   */
  palette: [string, string, string, string]
  light: ThemeStyles
  dark: ThemeStyles
}
