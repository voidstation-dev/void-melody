"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getRuntimeVersion } from "@/lib/runtime-version";
import {
  Home,
  Trash2,
  User,
  Mic,
  FileText,
  Music,
  Settings2,
  LayoutTemplate,
  Type,
  Download,
  MessageSquare,
  ChevronDown,
  Flame,
  Sparkles,
} from "lucide-react";

export function AppSidebar() {
  const pathname = usePathname();
  const [version, setVersion] = useState("dev");

  useEffect(() => {
    getRuntimeVersion().then(setVersion).catch(() => setVersion("dev"));
  }, []);

  const navItem = (
    href: string,
    label: string,
    Icon: any,
    active?: boolean,
  ) => {
    const isActive = active !== undefined ? active : pathname === href;
    return (
      <Link
        key={href}
        href={href}
        className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
          isActive
            ? "bg-muted text-foreground"
            : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        }`}
      >
        <Icon className="h-4 w-4" />
        {label}
      </Link>
    );
  };

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-border bg-card">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <nav className="space-y-1">
          {navItem("/", "Generate", Mic)}
          {navItem("/vieneu", "Voice Lab", Sparkles)}
          {navItem("/voices", "Voices", User)}
          {navItem("/history", "History", FileText)}
          {navItem("/settings", "Settings", Settings2)}
        </nav>
      </div>

      <div className="p-4 border-t border-border mt-auto">
        <div className="flex flex-col gap-1 rounded-xl bg-muted/50 p-4 border border-border/50">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-full bg-primary/20 flex items-center justify-center text-primary">
              <Flame className="w-3.5 h-3.5" />
            </div>
            <span className="font-bold text-sm text-foreground">Melody</span>
          </div>
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mt-2">
            Created by VoidStation
          </p>
          <p className="text-[10px] text-muted-foreground/60">
            v{version}
          </p>
        </div>
      </div>
    </aside>
  );
}
