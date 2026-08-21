import { en } from "./en";
import { vi } from "./vi";
import { Locale, TranslationKey, TranslationSchema } from "./types";

export * from "./types";
export { vi, en };

export const dictionaries: Record<Locale, TranslationSchema> = {
  vi,
  en,
};

export const defaultLocale: Locale = "vi";

export function getTranslation(
  locale: Locale,
  key: TranslationKey,
  params?: Record<string, string | number>,
): string {
  const dictionary = dictionaries[locale] || dictionaries[defaultLocale];
  const keys = key.split(".");
  let current: any = dictionary;

  for (const k of keys) {
    if (current && typeof current === "object" && k in current) {
      current = current[k];
    } else {
      // Fallback to Vietnamese dictionary if key missing
      let fallback: any = dictionaries[defaultLocale];
      for (const fk of keys) {
        if (fallback && typeof fallback === "object" && fk in fallback) {
          fallback = fallback[fk];
        } else {
          return key;
        }
      }
      current = fallback;
      break;
    }
  }

  if (typeof current !== "string") {
    return key;
  }

  if (!params) {
    return current;
  }

  return current.replace(/{(\w+)}/g, (_, match) => {
    return params[match] !== undefined ? String(params[match]) : `{${match}}`;
  });
}
