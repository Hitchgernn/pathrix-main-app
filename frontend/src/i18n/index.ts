import { useCallback } from "react";
import { useStore } from "../store";
import { id } from "./id";
import { en } from "./en";

/** Two locales, no dependency.
 *
 *  `id.ts` defines the key set and `en.ts` is typed against it, so a missing
 *  key, an extra key, or a mismatched argument list is a build error rather
 *  than a string that silently renders as its own name. `npx tsc` is the test
 *  suite for translations.
 *
 *  An i18n library would add 30-45KB of runtime for about 130 strings, in an
 *  app whose other open task this round was making the bundle lighter.
 *  Indonesian has no plural inflection either, so the one thing a library would
 *  really buy us is a rule only English needs.
 */

export type Locale = "id" | "en";

/** Values widen to `string`, so `en` is free to differ in wording while still
 *  being held to the same keys and the same call signatures. */
export type Messages = {
  [K in keyof typeof id]: (typeof id)[K] extends (...args: infer A) => string
    ? (...args: A) => string
    : string;
};

export type MessageKey = keyof Messages;

type Args<K extends MessageKey> = Messages[K] extends (...args: infer A) => string ? A : [];

const CATALOGUES: Record<Locale, Messages> = { id, en };


/** Translate outside React — module code, event handlers, the store. */
export function translate<K extends MessageKey>(
  locale: Locale,
  key: K,
  ...args: Args<K>
): string {
  const value = CATALOGUES[locale][key];
  return typeof value === "function"
    ? (value as (...a: unknown[]) => string)(...(args as unknown[]))
    : (value as string);
}

/** The hook every component uses. Re-renders on a locale change because it
 *  subscribes to the store slice. */
export function useT() {
  const locale = useStore((s) => s.locale);
  return useCallback(
    <K extends MessageKey>(key: K, ...args: Args<K>) => translate(locale, key, ...args),
    [locale],
  );
}

/** For modules that need the locale itself: Intl formatting, `<html lang>`. */
export const currentLocale = (): Locale => useStore.getState().locale;
