import { fallbackBundle, flatten, type Nested } from "./fallback";
import type { TranslationBundle } from "./fallback";

type Loader = () => Promise<Nested>;

/** One lazy chunk per locale file other than the bundled `de` and `en`. */
const LAZY_LOCALE_FILES = import.meta.glob<Nested>(
  ["./fallback/*.json", "!./fallback/de.json", "!./fallback/en.json"],
  { import: "default" },
);

function codeOf(path: string): string {
  return path.replace(/^.*\//, "").replace(/\.json$/, "");
}

async function loadLazy(
  load: Loader,
  locale: string,
): Promise<TranslationBundle> {
  try {
    return flatten(await load());
  } catch {
    // A failed chunk fetch degrades to English; the UI never breaks on it.
    return fallbackBundle(locale);
  }
}

/** A `loadBundle` over `files` (a glob result): lazy chunks for known locales, bundled strings otherwise. */
export function createBundleLoader(
  files: Record<string, Loader>,
): (locale: string) => Promise<TranslationBundle> {
  const loaders = new Map(
    Object.entries(files).map(([path, load]) => [codeOf(path), load]),
  );
  return async (locale) => {
    const load = loaders.get(locale);
    return load ? loadLazy(load, locale) : fallbackBundle(locale);
  };
}

/** Strings for `locale`: bundled for `de` and `en`, a code-split chunk for the rest, `en` when unknown. */
export const loadBundle = createBundleLoader(LAZY_LOCALE_FILES);
