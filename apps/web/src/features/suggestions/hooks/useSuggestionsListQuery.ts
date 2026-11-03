import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchSuggestions } from "../services/suggestionsApi";
import type { SuggestionListResponse, SuggestionStatusFilter } from "../types";

export interface SuggestionsListFilters {
  status: SuggestionStatusFilter;
  kind: string | null;
  jurisdictionId: string | null;
}

function statusParam(status: SuggestionStatusFilter): string[] | undefined {
  return status === "all" ? undefined : [status];
}

export function useSuggestionsListQuery({
  status,
  kind,
  jurisdictionId,
}: SuggestionsListFilters) {
  const { locale } = useLocale();

  return useApiQuery<SuggestionListResponse>(
    queryKeys.suggestions.list({ status, kind, jurisdictionId }, locale),
    () =>
      fetchSuggestions({
        locale,
        status: statusParam(status),
        kind: kind ?? undefined,
        jurisdictionId: jurisdictionId ?? undefined,
      }),
    { placeholderData: keepPreviousData },
  );
}
