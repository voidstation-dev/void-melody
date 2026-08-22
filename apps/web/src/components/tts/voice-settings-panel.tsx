"use client";

import { useState } from "react";
import Link from "next/link";
import { AudioLines, Check, ChevronsUpDown, Plus, SlidersHorizontal, Sparkles, User, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/hooks/use-translation";
import { cn } from "@/lib/utils";
import { Voice, CustomVoice } from "@/types/voice";

type VoiceSettingsPanelProps = {
  voices: Voice[];
  customVoices?: CustomVoice[];
  selectedVoice: string;
  onSelectVoice: (v: string) => void;
  rate: number;
  onRateChange: (r: number) => void;
  onGenerate?: () => void;
  isSubmitting?: boolean;
};

const CustomSlider = ({
  label,
  left,
  right,
  value,
  onChange,
  min = 0,
  max = 2,
  step = 0.1,
}: {
  label: string;
  left: string;
  right: string;
  value: number;
  onChange: (val: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) => {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-4 shadow-xs">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-foreground">{label}</span>
        <div className="rounded-md bg-primary/10 px-2 py-1 text-xs font-bold text-primary">
          {value.toFixed(1)}x
        </div>
      </div>

      <div className="relative flex h-6 w-full items-center">
        <div className="pointer-events-none absolute top-1/2 h-1.5 w-full -translate-y-1/2 rounded-full bg-muted" />
        <div
          className="pointer-events-none absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-primary"
          style={{ width: `${percentage}%` }}
        />
        <div
          className="pointer-events-none absolute h-4 w-4 rounded-full border-2 border-primary bg-background shadow-md"
          style={{ left: `calc(${percentage}% - 8px)` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(parseFloat(event.target.value))}
          className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
        />
      </div>

      <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  );
};

const presetStyleLabels: Record<string, string> = {
  tu_nhien: "Tự nhiên",
  tin_tuc: "Tin tức",
  doc_truyen: "Đọc truyện",
};

function presetMetadata(voice: Voice) {
  const gender = voice.gender === "male" ? "Nam" : voice.gender === "female" ? "Nữ" : null;
  const style = voice.style ? presetStyleLabels[voice.style] || voice.style : null;
  const metadata = [gender, voice.region, style].filter(Boolean);
  return metadata.length > 0 ? metadata.join(" · ") : voice.description || `${voice.languageCode || "vi-VN"} · Giọng mẫu`;
}

export function VoiceSettingsPanel({
  voices,
  customVoices = [],
  selectedVoice,
  onSelectVoice,
  rate,
  onRateChange,
}: VoiceSettingsPanelProps) {
  const { t } = useTranslation();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [filterTab, setFilterTab] = useState<"all" | "preset" | "custom">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [presetRegion, setPresetRegion] = useState("all");
  const [presetGender, setPresetGender] = useState("all");

  const currentPresetVoice = voices.find((voice) => voice.voiceType === selectedVoice);
  const currentCustomVoice = customVoices.find((voice) => voice.id === selectedVoice);
  const isCustomSelected = !!currentCustomVoice;
  const currentDisplayName = currentCustomVoice
    ? currentCustomVoice.display_name
    : currentPresetVoice?.displayName || t("common.select");
  const currentSubtitle = currentCustomVoice
    ? `VieNeu · ${currentCustomVoice.quality_score ? `${currentCustomVoice.quality_score}/100 · ` : ""}${t("generate.customVoiceBadge")}`
    : currentPresetVoice
      ? `${currentPresetVoice.languageCode || "vi-VN"} · ${t("generate.presetVoiceBadge")}`
      : t("common.none");

  const query = searchQuery.toLowerCase().trim();
  const filteredPresets = voices.filter(
    (voice) =>
      (!query || `${voice.displayName} ${voice.voiceType} ${voice.description || ""} ${presetMetadata(voice)}`.toLowerCase().includes(query)) &&
      (presetRegion === "all" || voice.region === presetRegion) &&
      (presetGender === "all" || voice.gender === presetGender),
  );
  const filteredCustoms = customVoices.filter(
    (voice) =>
      !query ||
      voice.display_name.toLowerCase().includes(query) ||
      (voice.transcript && voice.transcript.toLowerCase().includes(query)),
  );
  const showCustoms = filterTab === "all" || filterTab === "custom";
  const showPresets = filterTab === "all" || filterTab === "preset";
  const regions = Array.from(new Set(voices.map((voice) => voice.region).filter(Boolean))) as string[];
  const genders = Array.from(new Set(voices.map((voice) => voice.gender).filter(Boolean))) as string[];
  const presetFiltersActive = presetRegion !== "all" || presetGender !== "all";
  const vieneuPresetCount = voices.filter((voice) => voice.providerId === "vieneu").length || voices.length;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="mb-4 text-xs font-extrabold uppercase tracking-widest text-muted-foreground">
          {t("generate.selectedVoice")}
        </h3>

        <Popover open={isDropdownOpen} onOpenChange={setIsDropdownOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              role="combobox"
              aria-label={t("generate.selectedVoice")}
              aria-expanded={isDropdownOpen}
              variant="outline"
              className={cn(
                "group h-auto min-h-[76px] w-full justify-between rounded-2xl border bg-card p-3.5 text-left shadow-none",
                isDropdownOpen ? "border-primary ring-4 ring-primary/10" : "border-border hover:border-primary/50 hover:shadow-xs",
              )}
            >
              <span className="flex min-w-0 items-center gap-3.5">
                <span className={cn(
                  "flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border shadow-2xs transition-all",
                  isCustomSelected
                    ? "border-violet-500/25 bg-violet-500/15 text-violet-600 group-hover:bg-violet-500/20 dark:text-violet-400"
                    : "border-primary/20 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent text-primary group-hover:from-primary/25",
                )}>
                  {isCustomSelected ? <Sparkles className="h-5 w-5" /> : <AudioLines className="h-5 w-5" />}
                </span>
                <span className="flex min-w-0 flex-col items-start">
                  <span className="flex max-w-full items-center gap-2">
                    <span className="truncate text-base font-bold text-foreground">{currentDisplayName}</span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "shrink-0 border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400",
                        isCustomSelected && "border-violet-500/20 bg-violet-500/10 text-violet-600 dark:text-violet-400",
                      )}
                    >
                      {isCustomSelected ? "Clone" : t("generate.presetVoiceBadge")}
                    </Badge>
                  </span>
                  <span className="mt-0.5 truncate text-xs font-medium text-muted-foreground">{currentSubtitle}</span>
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2.5 pr-1">
                <span className="hidden text-[11px] font-bold uppercase tracking-wider text-primary opacity-0 transition-opacity duration-200 group-hover:opacity-100 sm:block">
                  {t("generate.changeVoice")}
                </span>
                <ChevronsUpDown className={cn("h-4 w-4 text-muted-foreground transition-colors group-hover:text-foreground", isDropdownOpen && "text-primary")} />
              </span>
            </Button>
          </PopoverTrigger>

          <PopoverContent
            align="start"
            sideOffset={8}
            className="w-[var(--radix-popover-trigger-width)] min-w-[320px] overflow-hidden rounded-[1.25rem] border-border/80 bg-card p-0 shadow-2xl"
          >
            <Command label={t("voices.searchLabel")} shouldFilter={false} className="rounded-none bg-transparent p-0">
              <div className="border-b border-border bg-muted/20 p-3">
                <div className="mb-2 flex items-center justify-between px-1">
                  <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.16em] text-primary">
                    <AudioLines className="h-3.5 w-3.5" />
                    <span>VieNeu · Preset library</span>
                  </div>
                  <Badge variant="secondary" className="h-6 bg-primary/10 px-2 text-[10px] font-black text-primary">
                    {vieneuPresetCount} giọng
                  </Badge>
                </div>

                <CommandInput
                  aria-label={t("voices.searchLabel")}
                  placeholder={t("voices.searchPlaceholder")}
                  value={searchQuery}
                  onValueChange={setSearchQuery}
                />

                <div className="mt-2 flex items-center gap-1 rounded-2xl bg-muted/60 p-1 text-xs font-bold">
                  {([
                    ["all", `${t("common.all")} (${voices.length + customVoices.length})`],
                    ["preset", `${t("voices.presetBadge")} (${voices.length})`],
                    ["custom", `${t("voices.tabCustom")} (${customVoices.length})`],
                  ] as const).map(([tab, label]) => (
                    <Button
                      key={tab}
                      type="button"
                      variant={filterTab === tab ? "secondary" : "ghost"}
                      onClick={() => setFilterTab(tab)}
                      className="h-8 min-w-0 flex-1 rounded-xl px-2 text-xs shadow-none"
                    >
                      {tab === "custom" && <Sparkles className="h-3 w-3 text-violet-500" />}
                      <span>{label}</span>
                    </Button>
                  ))}
                </div>

                {voices.length > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <SlidersHorizontal className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <select
                      aria-label="Lọc vùng giọng"
                      value={presetRegion}
                      onChange={(event) => setPresetRegion(event.target.value)}
                      className="min-w-0 flex-1 rounded-xl border border-border bg-background px-2.5 py-1.5 text-[11px] font-bold text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                    >
                      <option value="all">Tất cả vùng giọng</option>
                      {regions.map((region) => <option key={region} value={region}>{region}</option>)}
                    </select>
                    <select
                      aria-label="Lọc giới tính"
                      value={presetGender}
                      onChange={(event) => setPresetGender(event.target.value)}
                      className="min-w-0 flex-1 rounded-xl border border-border bg-background px-2.5 py-1.5 text-[11px] font-bold text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                    >
                      <option value="all">Tất cả chất giọng</option>
                      {genders.map((gender) => <option key={gender} value={gender}>{gender === "male" ? "Nam" : "Nữ"}</option>)}
                    </select>
                    {presetFiltersActive && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => { setPresetRegion("all"); setPresetGender("all"); }}
                        className="h-8 w-8 shrink-0 rounded-xl text-muted-foreground hover:text-foreground"
                        aria-label="Xóa bộ lọc giọng"
                        title="Xóa bộ lọc"
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                )}
              </div>

              <ScrollArea className="h-[22rem]">
                <CommandList label="Chọn giọng đọc" className="max-h-none p-2">
                  {showCustoms && (
                    <CommandGroup heading={t("generate.tabMyVoices")}>
                      <div className="mb-1 flex items-center justify-end px-2">
                        <Link href="/vieneu" onClick={() => setIsDropdownOpen(false)} className="inline-flex items-center gap-1 text-[11px] font-bold text-primary hover:underline">
                          <Plus className="h-3 w-3" />
                          <span>{t("voices.newVoice")}</span>
                        </Link>
                      </div>
                      {filteredCustoms.map((voice) => {
                        const isSelected = selectedVoice === voice.id;
                        return (
                          <CommandItem
                            key={voice.id}
                            value={voice.id}
                            data-checked={isSelected}
                            aria-selected={isSelected}
                            onSelect={() => { onSelectVoice(voice.id); setIsDropdownOpen(false); }}
                            className={cn(
                              "mb-1 min-h-14 rounded-2xl border border-transparent px-3 py-2.5 text-sm",
                              isSelected ? "bg-primary font-semibold text-primary-foreground shadow-xs" : "text-foreground hover:border-violet-500/20 hover:bg-violet-500/10",
                            )}
                          >
                            <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-xl", isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-violet-500/10 text-violet-600 dark:text-violet-400")}>
                              <User className="h-4 w-4" />
                            </span>
                            <span className="flex min-w-0 flex-1 flex-col">
                              <span className="truncate">{voice.display_name}</span>
                              <span className={cn("text-[10px]", isSelected ? "text-primary-foreground/80" : "text-muted-foreground")}>
                                VieNeu · {voice.quality_score ? `${voice.quality_score}/100 · ` : ""}{t("generate.customVoiceBadge")}
                              </span>
                            </span>
                            {isSelected && <Check className="ml-auto h-4 w-4 shrink-0" />}
                          </CommandItem>
                        );
                      })}
                      {filteredCustoms.length === 0 && filterTab === "custom" && (
                        <div className="my-1 rounded-2xl border border-dashed border-border/80 bg-muted/20 p-4 text-center">
                          <p className="text-xs text-muted-foreground">{t("generate.noCustomVoices")}</p>
                          <Link href="/vieneu" onClick={() => setIsDropdownOpen(false)} className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline">
                            <Plus className="h-3.5 w-3.5" />
                            <span>{t("generate.createInVoiceLab")}</span>
                          </Link>
                        </div>
                      )}
                    </CommandGroup>
                  )}

                  {showCustoms && showPresets && <CommandSeparator />}

                  {showPresets && (
                    <CommandGroup heading={t("generate.tabPresetVoices")}>
                      {filteredPresets.map((voice) => {
                        const isSelected = selectedVoice === voice.voiceType;
                        return (
                          <CommandItem
                            key={voice.voiceType}
                            value={voice.voiceType}
                            data-checked={isSelected}
                            aria-selected={isSelected}
                            onSelect={() => { onSelectVoice(voice.voiceType); setIsDropdownOpen(false); }}
                            className={cn(
                              "mb-1 min-h-14 rounded-2xl border border-transparent px-3 py-2.5 text-sm",
                              isSelected ? "bg-primary font-semibold text-primary-foreground shadow-xs" : "text-foreground hover:border-border/60 hover:bg-muted",
                            )}
                          >
                            <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-xl", isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400")}>
                              <AudioLines className="h-4 w-4" />
                            </span>
                            <span className="flex min-w-0 flex-1 flex-col">
                              <span className="truncate">{voice.displayName}</span>
                              <span className={cn("text-[10px]", isSelected ? "text-primary-foreground/80" : "text-muted-foreground")}>
                                {presetMetadata(voice)}
                              </span>
                            </span>
                            {isSelected && <Check className="ml-auto h-4 w-4 shrink-0" />}
                          </CommandItem>
                        );
                      })}
                    </CommandGroup>
                  )}

                  <CommandEmpty>{t("generate.noMatchingVoices")}</CommandEmpty>
                </CommandList>
              </ScrollArea>

              <div className="flex shrink-0 items-center justify-between border-t border-border bg-muted/30 p-2 text-xs">
                <Link href="/vieneu" onClick={() => setIsDropdownOpen(false)} className="inline-flex items-center gap-1.5 px-2 py-1 font-bold text-primary hover:underline">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>{t("nav.voiceLab")}</span>
                </Link>
                <Link href="/voices" onClick={() => setIsDropdownOpen(false)} className="px-2 py-1 font-semibold text-muted-foreground hover:text-foreground">
                  {t("nav.voices")}
                </Link>
              </div>
            </Command>
          </PopoverContent>
        </Popover>
      </div>

      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">
            {t("generate.toneProperties")}
          </h3>
        </div>
        <div className="space-y-4">
          <CustomSlider
            label={t("generate.speed")}
            left={t("generate.slower")}
            right={t("generate.faster")}
            min={0.5}
            max={2.0}
            step={0.1}
            value={rate}
            onChange={onRateChange}
          />
        </div>
      </div>
    </div>
  );
}
