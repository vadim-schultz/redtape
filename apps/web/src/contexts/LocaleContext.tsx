import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { initialLocale } from "../i18n/initialLocale";
import { fallbackBundle } from "../i18n/fallback";
import { useRemoteTranslations } from "../hooks/useRemoteTranslations";

export type LocaleContextValue = {
  locale: string;
  setLocale: (next: string) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  isLoading: boolean;
};

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [locale, setLocaleState] = useState(() => initialLocale());
  const { remote, isLoading } = useRemoteTranslations(locale);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const translations = useMemo(
    () => ({ ...fallbackBundle(locale), ...remote }),
    [locale, remote],
  );

  const setLocale = useCallback(
    (next: string) => {
      window.localStorage.setItem("locale", next);
      setLocaleState(next);
      // Ensure localized reads re-fetch when locale changes.
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
