"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getRuntimeVersion } from "@/lib/runtime-version";
import { useTranslation } from "@/hooks/use-translation";
import {
  Mic,
  FileText,
  Settings2,
  Flame,
  Sparkles,
  User,
  Clapperboard,
} from "lucide-react";

export function AppSidebar() {
  const pathname = usePathname();
  const { t } = useTranslation();
  const [version, setVersion] = useState("dev");

  useEffect(() => {
    getRuntimeVersion().then(setVersion).catch(() => setVersion("dev"));
  }, []);

  const navItem = (
    href: string,
    label: string,
    Icon: React.ComponentType<{ className?: string }>,
    active?: boolean,
  ) => {
    const isActive = active !== undefined ? active : pathname === href;
    return (
      <Link
        key={href}
        href={href}
        className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all ${
          isActive
            ? "bg-primary/10 text-primary font-bold shadow-xs"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        }`}
      >
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </Link>
    );
  };

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-border bg-card">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <nav className="space-y-1.5">
          {navItem("/", t("nav.generate"), Mic)}
          {navItem("/scripts", t("nav.scripts"), Clapperboard)}
          {navItem("/vieneu", t("nav.voiceLab"), Sparkles)}
          {navItem("/voices", t("nav.voices"), User)}
          {navItem("/history", t("nav.history"), FileText)}
          {navItem("/settings", t("nav.settings"), Settings2)}
        </nav>
      </div>

      <div className="p-4 border-t border-border mt-auto">
        <div className="flex flex-col gap-1 rounded-2xl bg-muted/50 p-4 border border-border/50">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
              <Flame className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm text-foreground">Melody</span>
          </div>
          <p className="text-[10px] text-muted-foreground font-medium tracking-wide mt-2">
            {t("nav.brandSubtitle")}
          </p>
          <p className="text-[10px] text-muted-foreground/70">
            {t("nav.version")}: v{version}
          </p>
        </div>
      </div>
    </aside>
  );
}
