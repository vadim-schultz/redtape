import { useMemo } from "react";

import type { TranslationBundle } from "../i18n/fallback";
import { useLocaleBundle } from "./useLocaleBundle";
import { useRemoteTranslations } from "./useRemoteTranslations";

/** The bundled or lazy locale strings with the remote `/translations` override on top. */
export function useTranslations(locale: string): {
  translations: TranslationBundle;
  isLoading: boolean;
} {
  const bundle = useLocaleBundle(locale);
  const { remote, isLoading } = useRemoteTranslations(locale);
  const translations = useMemo(
    () => ({ ...bundle, ...remote }),
    [bundle, remote],
  );
  return { translations, isLoading };
}
