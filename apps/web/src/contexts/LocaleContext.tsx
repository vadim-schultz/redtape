import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { buildApiUrl } from "../services/apiOrigin";

type TranslationBundle = Record<string, string>;

export type LocaleContextValue = {
  locale: string;
  setLocale: (next: string) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  isLoading: boolean;
};

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

function initialLocale() {
  return (
    window.localStorage.getItem("locale") ??
    navigator.language.slice(0, 2) ??
    "de"
  );
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [locale, setLocaleState] = useState(() => initialLocale());
  const [translations, setTranslations] = useState<TranslationBundle>({});
  const [isLoading, setIsLoading] = useState(true);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;

    setIsLoading(true);
    const translationsUrl = buildApiUrl("/api/v1/translations");
    translationsUrl.searchParams.set("locale", locale);
    fetch(translationsUrl.toString(), {
      headers: { "Accept-Language": locale },
      signal: abort.signal,
    })
      .then(async (res) => {
        if (!res.ok)
          throw new Error(`Translations request failed: ${res.status}`);
        const data = (await res.json()) as {
          locale: string;
          translations: TranslationBundle;
        };
        setTranslations(data.translations ?? {});
      })
      .catch(() => {
        // Keep UI usable even if API is down during dev.
        setTranslations({});
      })
      .finally(() => {
        setIsLoading(false);
      });

    return () => abort.abort();
  }, [locale]);

  const setLocale = useCallback(
    (next: string) => {
      window.localStorage.setItem("locale", next);
      setLocaleState(next);
      // Ensure domain reads re-fetch when locale changes.
      queryClient.invalidateQueries({ queryKey: ["*"] });
    },
    [queryClient],
  );

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      let value = translations[key] ?? key;
      if (params) {
        for (const [pKey, pVal] of Object.entries(params)) {
          value = value.replaceAll(`{${pKey}}`, String(pVal));
        }
      }
      return value;
    },
    [translations],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, isLoading }),
    [locale, setLocale, t, isLoading],
  );

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}
