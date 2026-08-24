
import React, { useState } from "react";
import { KeyRound, Sparkles, Loader2, AlertCircle, ClipboardPaste, X, Globe, Radio } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useTranslation } from "@/hooks/use-translation";
import { Locale } from "@/locales";
import { DEFAULT_DEV_KEY } from "@/constants";
import { BrandMark } from "@/components/ui/brand-logo";

export function LoginScreen() {
  const { login, isLoading } = useAuth();
  const { t, locale, setLocale } = useTranslation();
  const [inputKey, setInputKey] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputKey.trim();
    if (!trimmed) {
      setErrorMessage(t("auth.keyRequired"));
      return;
    }

    setErrorMessage(null);
    const result = await login(trimmed);
    if (!result.success) {
      setErrorMessage(t("auth.invalidKey"));
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setInputKey(text.trim());
        setErrorMessage(null);
      }
    } catch {
      // Ignore clipboard read errors
    }
  };

  const applyDevKey = () => {
    setInputKey(DEFAULT_DEV_KEY);
    setErrorMessage(null);
  };

  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center bg-gradient-to-b from-background via-muted/20 to-background p-4 font-sans text-foreground selection:bg-primary/20 sm:p-8">
      {/* Top bar with Language Selector */}
      <div className="absolute top-4 right-4 flex items-center gap-2 sm:top-6 sm:right-6">
        <div className="flex items-center gap-1.5 rounded-xl border border-border/80 bg-card/80 px-3 py-1.5 text-xs font-semibold shadow-xs backdrop-blur-sm">
          <Globe className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            aria-label="Language"
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
            className="bg-transparent text-xs font-semibold text-foreground outline-none cursor-pointer"
          >
            <option value="vi">Tiếng Việt</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>

      {/* Main Activation Card */}
      <div className="w-full max-w-md animate-in fade-in zoom-in-95 duration-300">
        <div className="overflow-hidden rounded-3xl border border-border/80 bg-card/90 p-6 sm:p-8 shadow-xl backdrop-blur-md">
          {/* Brand Logo & Icon */}
          <div className="flex flex-col items-center text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-card shadow-md ring-1 ring-border/60 overflow-hidden p-2">
              <BrandMark className="h-full w-full" alt="Melody" />
            </div>
            <h1 className="mt-5 text-xl font-extrabold tracking-tight sm:text-2xl">
              {t("auth.title")}
            </h1>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground sm:text-sm">
              {t("auth.subtitle")}
            </p>
          </div>

          {/* Activation Form */}
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="license-key-input" className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Access Key
              </label>
              <div className="relative flex items-center">
                <div className="pointer-events-none absolute left-3.5 flex items-center text-muted-foreground">
                  <KeyRound className="h-4 w-4" />
                </div>
                <input
                  id="license-key-input"
                  type="text"
                  value={inputKey}
                  onChange={(e) => {
                    setInputKey(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  disabled={isLoading}
                  placeholder={t("auth.keyPlaceholder")}
                  autoComplete="off"
                  spellCheck={false}
                  className={`w-full rounded-xl border bg-background py-3 pl-10 pr-20 text-sm font-medium text-foreground outline-none transition-all placeholder:text-muted-foreground/60 ${
                    errorMessage
                      ? "border-destructive/80 ring-2 ring-destructive/20 focus:border-destructive"
                      : "border-border/80 focus:border-primary focus:ring-4 focus:ring-primary/15"
                  }`}
                />
                {/* Actions inside input */}
                <div className="absolute right-2 flex items-center gap-1">
                  {inputKey ? (
                    <button
                      type="button"
                      onClick={() => setInputKey("")}
                      className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                      title={t("auth.clearBtn")}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handlePaste}
                      className="inline-flex items-center gap-1 rounded-lg border border-border/60 bg-muted/60 px-2 py-1 text-[11px] font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                      title={t("auth.pasteBtn")}
                    >
                      <ClipboardPaste className="h-3 w-3" />
                      <span>{t("auth.pasteBtn")}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs font-semibold text-destructive animate-in fade-in duration-200"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !inputKey.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-bold text-primary-foreground shadow-md shadow-primary/20 transition-all hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{t("auth.activatingBtn")}</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>{t("auth.activateBtn")}</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Key Helper */}
          <div className="mt-6 border-t border-border/50 pt-4 text-center">
            <button
              type="button"
              onClick={applyDevKey}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10 transition-colors"
            >
              <span>{t("auth.demoKeyNotice")}</span>
            </button>
          </div>
        </div>

        {/* Footer Support Notice */}
        <p className="mt-6 text-center text-xs text-muted-foreground">
          {t("auth.needHelp")} · <span className="font-semibold text-foreground">Void Station</span>
        </p>
      </div>
    </div>
  );
}
