import de from "./de.json";
import en from "./en.json";

export type TranslationBundle = Record<string, string>;

export type Nested = { [key: string]: string | Nested };

/** Flatten a nested locale file into dotted keys (`a: { b: "x" }` becomes `a.b`). */
export function flatten(tree: Nested, prefix = ""): TranslationBundle {
  return Object.entries(tree).reduce<TranslationBundle>((acc, [key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "string"
      ? { ...acc, [path]: value }
      : { ...acc, ...flatten(value, path) };
  }, {});
}

const bundles: Record<string, TranslationBundle> = {
  en: flatten(en),
  de: flatten(de),
};

/**
 * Bundled UI strings, so the chrome never renders raw keys while the API wakes up.
 *
 * Only `de` (the default) and `en` (the last resort) are bundled; every other
 * locale loads lazily through `loadBundle` and shows `en` until it arrives.
 */
export function fallbackBundle(locale: string): TranslationBundle {
  return bundles[locale] ?? bundles.en;
}
