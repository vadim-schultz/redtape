import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchSuggestionDetail } from "../services/suggestionsApi";
import type { SuggestionRead } from "../types";

export function useSuggestionDetailQuery(id?: string) {
  const { locale } = useLocale();

  return useApiQuery<SuggestionRead>(
    queryKeys.suggestions.detail(id),
    () => fetchSuggestionDetail({ locale, id: id as string }),
    { enabled: !!id },
  );
}
