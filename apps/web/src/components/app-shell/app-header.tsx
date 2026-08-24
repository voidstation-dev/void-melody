import { BrandMark } from "@/components/ui/brand-logo"
import { ThemeToggle } from "@/components/ui/theme-toggle"
import { LanguageToggle } from "@/components/ui/language-toggle"

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-center gap-2.5">
        <BrandMark className="h-8 w-8" />
        <span className="text-xl font-extrabold tracking-tight">Melody</span>
      </div>

      <div className="flex items-center gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>
    </header>
  );
}
