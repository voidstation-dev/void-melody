"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Voice, CustomVoice } from "@/types/voice";
import { ChevronDown, Check, Sparkles, Plus, Search, User, AudioLines } from "lucide-react";
import { useTranslation } from "@/hooks/use-translation";

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
    <div className="flex flex-col gap-4 p-4 rounded-2xl bg-card border border-border shadow-xs">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-foreground">{label}</span>
        <div className="px-2 py-1 rounded-md bg-primary/10 text-primary text-xs font-bold">
          {value.toFixed(1)}x
        </div>
      </div>
      
      <div className="relative flex items-center h-6 w-full">
        {/* Track background */}
        <div className="absolute w-full h-1.5 top-1/2 -translate-y-1/2 rounded-full bg-muted pointer-events-none" />
        {/* Track fill */}
        <div 
          className="absolute h-1.5 top-1/2 -translate-y-1/2 rounded-full bg-primary pointer-events-none"
          style={{ width: `${percentage}%` }}
        />
        {/* Custom Thumb */}
        <div 
          className="absolute h-4 w-4 bg-background border-2 border-primary rounded-full shadow-md pointer-events-none"
          style={{ left: `calc(${percentage}% - 8px)` }}
        />
        {/* Interactive Invisible Input */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange && onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />
      </div>
      
      <div className="flex items-center justify-between text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  );
};

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
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Find currently active voice (could be preset or custom)
  const currentPresetVoice = voices.find((v) => v.voiceType === selectedVoice);
  const currentCustomVoice = customVoices.find((v) => v.id === selectedVoice);
  const isCustomSelected = !!currentCustomVoice;

  const currentDisplayName = currentCustomVoice
    ? currentCustomVoice.display_name
    : currentPresetVoice?.displayName || t("common.select");

  const currentSubtitle = currentCustomVoice
    ? `VieNeu · ${currentCustomVoice.quality_score ? `${currentCustomVoice.quality_score}/100 · ` : ""}${t("generate.customVoiceBadge")}`
    : currentPresetVoice
      ? `${currentPresetVoice.languageCode || "vi-VN"} · ${t("generate.presetVoiceBadge")}`
      : t("common.none");

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const q = searchQuery.toLowerCase().trim();
  const filteredPresets = voices.filter(
    (v) => !q || v.displayName.toLowerCase().includes(q) || v.voiceType.toLowerCase().includes(q)
  );
  const filteredCustoms = customVoices.filter(
    (v) => !q || v.display_name.toLowerCase().includes(q) || (v.transcript && v.transcript.toLowerCase().includes(q))
  );

  const showCustoms = (filterTab === "all" || filterTab === "custom");
  const showPresets = (filterTab === "all" || filterTab === "preset");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="text-xs font-extrabold uppercase tracking-widest text-muted-foreground mb-4">
          {t("generate.selectedVoice")}
        </h3>

        <div className="relative" ref={dropdownRef}>
          <div
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className={`group flex items-center justify-between rounded-2xl bg-card p-3.5 border transition-all cursor-pointer ${
              isDropdownOpen 
                ? "border-primary ring-4 ring-primary/10 shadow-sm" 
                : "border-border hover:border-primary/50 hover:shadow-xs"
            }`}
          >
            <div className="flex items-center gap-3.5 min-w-0">
              <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl transition-all shadow-2xs ${
                isCustomSelected 
                  ? "bg-violet-500/15 text-violet-600 dark:text-violet-400 border border-violet-500/25 group-hover:bg-violet-500/20" 
                  : "bg-gradient-to-br from-primary/20 via-primary/10 to-transparent text-primary border border-primary/20 group-hover:from-primary/25"
              }`}>
                {isCustomSelected ? (
                  <Sparkles className="h-5 w-5" />
                ) : (
                  <AudioLines className="h-5 w-5" />
                )}
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-base font-bold text-foreground truncate">
                    {currentDisplayName}
                  </span>
                  {isCustomSelected ? (
                    <span className="shrink-0 rounded-full bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 text-[10px] font-bold text-violet-600 dark:text-violet-400">
                      Clone
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                      {t("generate.presetVoiceBadge")}
                    </span>
                  )}
                </div>
                <span className="text-xs font-medium text-muted-foreground truncate mt-0.5">
                  {currentSubtitle}
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-2.5 pr-1 shrink-0">
              <span className="hidden sm:block text-[11px] font-bold uppercase tracking-wider text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                {t("generate.changeVoice")}
              </span>
              <div className={`p-1.5 rounded-full transition-colors ${isDropdownOpen ? "bg-primary/10 text-primary" : "text-muted-foreground group-hover:text-foreground"}`}>
                <ChevronDown
                  className={`h-4 w-4 transition-transform duration-200 ${isDropdownOpen ? "rotate-180" : ""}`}
                />
              </div>
            </div>
          </div>

          {/* Custom Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute top-full left-0 right-0 mt-2 z-50 rounded-3xl border border-border bg-card shadow-2xl overflow-hidden flex flex-col max-h-[440px] animate-in fade-in zoom-in-95 duration-150 ring-1 ring-black/5 dark:ring-white/10">
              {/* Filter Tabs & Search Header */}
              <div className="p-3 border-b border-border bg-muted/20 flex flex-col gap-2.5 shrink-0">
                {/* Search box */}
                <div className="relative flex items-center">
                  <Search className="absolute left-3.5 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t("voices.searchPlaceholder")}
                    className="w-full rounded-2xl border border-border bg-background pl-9 pr-4 py-2 text-xs text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all font-medium"
                    autoFocus
                  />
                </div>

                {/* Filter Tabs */}
                <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-2xl text-xs font-bold">
                  <button
                    type="button"
                    onClick={() => setFilterTab("all")}
                    className={`flex-1 py-1.5 rounded-xl transition-all text-center ${
                      filterTab === "all"
                        ? "bg-card text-foreground shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t("common.all")} ({voices.length + customVoices.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterTab("preset")}
                    className={`flex-1 py-1.5 rounded-xl transition-all text-center ${
                      filterTab === "preset"
                        ? "bg-card text-foreground shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t("voices.presetBadge")} ({voices.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterTab("custom")}
                    className={`flex-1 py-1.5 rounded-xl transition-all text-center flex items-center justify-center gap-1 ${
                      filterTab === "custom"
                        ? "bg-card text-foreground shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Sparkles className="h-3 w-3 text-violet-500" />
                    <span>{t("voices.tabCustom")} ({customVoices.length})</span>
                  </button>
                </div>
              </div>

              {/* Voices List */}
              <div className="overflow-y-auto p-2 flex flex-col gap-4 flex-1">
                {/* MY CUSTOM VOICES SECTION */}
                {showCustoms && (
                  <div>
                    <div className="flex items-center justify-between px-2 py-1 mb-1">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-violet-600 dark:text-violet-400">
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>{t("generate.tabMyVoices")}</span>
                      </div>
                      <Link
                        href="/vieneu"
                        onClick={() => setIsDropdownOpen(false)}
                        className="text-[11px] font-bold text-primary hover:underline flex items-center gap-1"
                      >
                        <Plus className="h-3 w-3" />
                        <span>{t("voices.newVoice")}</span>
                      </Link>
                    </div>

                    {filteredCustoms.length > 0 ? (
                      <div className="flex flex-col gap-1">
                        {filteredCustoms.map((cv) => {
                          const isSelected = selectedVoice === cv.id;
                          return (
                            <div
                              key={cv.id}
                              onClick={() => {
                                onSelectVoice(cv.id);
                                setIsDropdownOpen(false);
                              }}
                              className={`flex items-center justify-between rounded-2xl px-3 py-2.5 text-sm cursor-pointer transition-all ${
                                isSelected
                                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                                  : "hover:bg-violet-500/10 text-foreground border border-transparent hover:border-violet-500/20"
                              }`}
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${
                                  isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-violet-500/10 text-violet-600 dark:text-violet-400"
                                }`}>
                                  <User className="h-4 w-4" />
                                </div>
                                <div className="flex flex-col min-w-0">
                                  <span className="truncate">{cv.display_name}</span>
                                  <span className={`text-[10px] ${isSelected ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
                                    VieNeu · {cv.quality_score ? `${cv.quality_score}/100 · ` : ""}{t("generate.customVoiceBadge")}
                                  </span>
                                </div>
                              </div>
                              {isSelected && <Check className="h-4 w-4 shrink-0" />}
                            </div>
                          );
                        })}
                      </div>
                    ) : filterTab === "custom" ? (
                      <div className="p-4 text-center rounded-2xl border border-dashed border-border/80 bg-muted/20 my-1">
                        <p className="text-xs text-muted-foreground">{t("generate.noCustomVoices")}</p>
                        <Link
                          href="/vieneu"
                          onClick={() => setIsDropdownOpen(false)}
                          className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline"
                        >
                          <Plus className="h-3.5 w-3.5" />
                          <span>{t("generate.createInVoiceLab")}</span>
                        </Link>
                      </div>
                    ) : null}
                  </div>
                )}

                {/* PRESET VOICES SECTION */}
                {showPresets && (
                  <div>
                    <div className="flex items-center gap-1.5 px-2 py-1 mb-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                      <AudioLines className="h-3.5 w-3.5" />
                      <span>{t("generate.tabPresetVoices")}</span>
                    </div>

                    {filteredPresets.length > 0 ? (
                      <div className="flex flex-col gap-1">
                        {filteredPresets.map((v) => {
                          const isSelected = selectedVoice === v.voiceType;
                          return (
                            <div
                              key={v.voiceType}
                              onClick={() => {
                                onSelectVoice(v.voiceType);
                                setIsDropdownOpen(false);
                              }}
                              className={`flex items-center justify-between rounded-2xl px-3 py-2.5 text-sm cursor-pointer transition-all ${
                                isSelected
                                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                                  : "hover:bg-muted text-foreground border border-transparent hover:border-border/60"
                              }`}
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${
                                  isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                }`}>
                                  <AudioLines className="h-4 w-4" />
                                </div>
                                <div className="flex flex-col min-w-0">
                                  <span className="truncate">{v.displayName}</span>
                                  <span
                                    className={`text-[10px] ${isSelected ? "text-primary-foreground/80" : "text-muted-foreground"}`}
                                  >
                                    {v.languageCode || "vi-VN"} · {t("voices.presetBadge")}
                                  </span>
                                </div>
                              </div>
                              {isSelected && <Check className="h-4 w-4 shrink-0" />}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="p-3 text-center text-xs text-muted-foreground">
                        {t("generate.noMatchingVoices")}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Dropdown Footer */}
              <div className="p-2 border-t border-border bg-muted/30 flex items-center justify-between text-xs shrink-0">
                <Link
                  href="/vieneu"
                  onClick={() => setIsDropdownOpen(false)}
                  className="inline-flex items-center gap-1.5 text-primary font-bold hover:underline px-2 py-1"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>{t("nav.voiceLab")}</span>
                </Link>
                <Link
                  href="/voices"
                  onClick={() => setIsDropdownOpen(false)}
                  className="text-muted-foreground hover:text-foreground font-semibold px-2 py-1"
                >
                  {t("nav.voices")}
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
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
