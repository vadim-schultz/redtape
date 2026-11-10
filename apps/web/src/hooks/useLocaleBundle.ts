import { useEffect, useState } from "react";

import { loadBundle } from "../i18n";
import { fallbackBundle, type TranslationBundle } from "../i18n/fallback";

type Loaded = { locale: string; bundle: TranslationBundle };

/** Interface strings for `locale`: bundled English until a lazy locale chunk arrives. */
export function useLocaleBundle(locale: string): TranslationBundle {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let current = true;
    loadBundle(locale).then((bundle) => {
      if (current) setLoaded({ locale, bundle });
    });
    return () => {
      current = false;
    };
  }, [locale]);

  return loaded?.locale === locale ? loaded.bundle : fallbackBundle(locale);
}
