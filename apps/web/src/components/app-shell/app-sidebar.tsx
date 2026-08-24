import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getRuntimeVersion } from "@/lib/runtime-version";
import { useTranslation } from "@/hooks/use-translation";
import { BrandMark } from "@/components/ui/brand-logo";
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
  const { t } = useTranslation();
  const [version, setVersion] = useState("dev");

  useEffect(() => {
    getRuntimeVersion().then(setVersion).catch(() => setVersion("dev"));
  }, []);

  const navItem = (
    to: string,
    label: string,
    Icon: React.ComponentType<{ className?: string }>,
  ) => {
    return (
      <Link
        key={to}
        to={to}
        activeOptions={{ exact: to === "/" }}
        activeProps={{
          className: "bg-primary/10 text-primary font-bold shadow-xs",
        }}
        inactiveProps={{
          className: "text-muted-foreground hover:bg-muted hover:text-foreground",
        }}
        className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all"
      >
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </Link>
    );
  };

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-border bg-card">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* TẠO */}
        <div className="space-y-1.5">
          <div className="px-3 text-[10px] font-extrabold tracking-wider text-muted-foreground/70 uppercase">
            {t("nav.groupCreate")}
          </div>
          <nav className="space-y-1">
            {navItem("/", t("nav.generate"), Mic)}
            {navItem("/vieneu", t("nav.voiceLab"), Sparkles)}
          </nav>
        </div>

        {/* THƯ VIỆN */}
        <div className="space-y-1.5">
          <div className="px-3 text-[10px] font-extrabold tracking-wider text-muted-foreground/70 uppercase">
            {t("nav.groupLibrary")}
          </div>
          <nav className="space-y-1">
            {navItem("/voices", t("nav.voices"), User)}
            {navItem("/history", t("nav.history"), FileText)}
          </nav>
        </div>

        {/* CÀI ĐẶT */}
        <div className="space-y-1.5">
          <div className="px-3 text-[10px] font-extrabold tracking-wider text-muted-foreground/70 uppercase">
            {t("nav.groupSettings")}
          </div>
          <nav className="space-y-1">
            {navItem("/settings", t("nav.settings"), Settings2)}
          </nav>
        </div>
      </div>

      <div className="p-4 border-t border-border mt-auto">
        <div className="flex flex-col gap-1 rounded-2xl bg-muted/50 p-4 border border-border/50">
          <div className="flex items-center gap-2">
            <BrandMark className="h-6 w-6" />
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
