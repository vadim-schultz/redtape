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
import { initialLocale } from "../i18n/initialLocale";
import { fallbackBundle, type TranslationBundle } from "../i18n/fallback";
import { buildApiUrl } from "../services/apiOrigin";

export type LocaleContextValue = {
  locale: string;
  setLocale: (next: string) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  isLoading: boolean;
};

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

async function fetchTranslations(
  locale: string,
  signal: AbortSignal,
): Promise<TranslationBundle> {
  const url = buildApiUrl("/api/v1/translations");
  url.searchParams.set("locale", locale);
  const res = await fetch(url.toString(), {
    headers: { "Accept-Language": locale },
    signal,
  });
  if (!res.ok) throw new Error(`Translations request failed: ${res.status}`);
  const data = (await res.json()) as { translations?: TranslationBundle };
  return data.translations ?? {};
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [locale, setLocaleState] = useState(() => initialLocale());
  const [remote, setRemote] = useState<TranslationBundle>({});
  const [isLoading, setIsLoading] = useState(true);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;

    setIsLoading(true);
    fetchTranslations(locale, abort.signal)
      .then(setRemote)
      // Bundled strings keep the UI usable while the API is down or waking up.
      .catch(() => setRemote({}))
      .finally(() => setIsLoading(false));

    return () => abort.abort();
  }, [locale]);

  const translations = useMemo(
    () => ({ ...fallbackBundle(locale), ...remote }),
    [locale, remote],
  );

  const setLocale = useCallback(
    (next: string) => {
      window.localStorage.setItem("locale", next);
      setLocaleState(next);
      // Ensure domain reads re-fetch when locale changes.
      queryClient.invalidateQueries();
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
