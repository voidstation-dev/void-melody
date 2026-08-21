"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { Locale, TranslationKey, defaultLocale, getTranslation } from "@/locales";

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
  isVi: boolean;
  isEn: boolean;
}

const STORAGE_KEY = "voidmelody_locale";

const I18nContext = createContext<I18nContextType | null>(null);

export function I18nProvider({
  children,
  initialLocale = defaultLocale,
}: {
  children: React.ReactNode;
  initialLocale?: Locale;
}) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window !== "undefined") {
      try {
        const savedLocale = localStorage.getItem(STORAGE_KEY) as Locale | null;
        if (savedLocale === "vi" || savedLocale === "en") {
          return savedLocale;
        }
      } catch {
        // Ignore localStorage access errors
      }
    }
    return initialLocale;
  });

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem(STORAGE_KEY, newLocale);
    } catch {
      // Ignore localStorage write errors
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = newLocale;
    }
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  const t = useCallback(
    (key: TranslationKey, params?: Record<string, string | number>) => {
      return getTranslation(locale, key, params);
    },
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
      isVi: locale === "vi",
      isEn: locale === "en",
    }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useTranslation(): I18nContextType {
  const context = useContext(I18nContext);
  if (!context) {
    // Fallback if rendered outside provider
    return {
      locale: defaultLocale,
      setLocale: () => {},
      t: (key: TranslationKey, params?: Record<string, string | number>) =>
        getTranslation(defaultLocale, key, params),
      isVi: true,
      isEn: false,
    };
  }
  return context;
}
