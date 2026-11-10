import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { initialLocale } from "../i18n/initialLocale";
import { intlTag } from "../i18n/localeMeta";
import { translate, type TranslateParams } from "../i18n/translate";
import { useEnabledLocaleGuard } from "../hooks/useEnabledLocaleGuard";
import { useDocumentLang } from "../hooks/useDocumentLang";
import { useTranslations } from "../hooks/useTranslations";

export type LocaleContextValue = {
  locale: string;
  setLocale: (next: string) => void;
  t: (key: string, params?: TranslateParams) => string;
  isLoading: boolean;
};

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [locale, setLocaleState] = useState(() => initialLocale());
  const { translations, isLoading } = useTranslations(locale);

  useDocumentLang(locale);

  const setLocale = useCallback(
    (next: string) => {
      window.localStorage.setItem("locale", next);
      setLocaleState(next);
      // Ensure localized reads re-fetch when locale changes.
      queryClient.invalidateQueries();
    },
    [queryClient],
  );

  useEnabledLocaleGuard(locale, setLocale);

  const t = useCallback(
    (key: string, params?: TranslateParams) =>
      translate(translations, intlTag(locale), key, params),
    [translations, locale],
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
