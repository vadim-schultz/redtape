import { useEffect, useState } from "react";

import type { TranslationBundle } from "../i18n/fallback";
import { fetchTranslations } from "../services/translationsApi";

export interface RemoteTranslations {
  remote: TranslationBundle;
  isLoading: boolean;
}

/** Load the remote bundle for `locale`; an empty bundle on failure. */
export function useRemoteTranslations(locale: string): RemoteTranslations {
  const [remote, setRemote] = useState<TranslationBundle>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const abort = new AbortController();

    setIsLoading(true);
    fetchTranslations(locale, abort.signal)
      .then(setRemote)
      // Bundled strings keep the UI usable while the API is down or waking up.
      .catch(() => setRemote({}))
      .finally(() => setIsLoading(false));

    return () => abort.abort();
  }, [locale]);

  return { remote, isLoading };
}
