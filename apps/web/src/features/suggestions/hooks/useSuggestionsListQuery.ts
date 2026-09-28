import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchSuggestions } from "../services/suggestionsApi";
import type { SuggestionListResponse } from "../types";
import type { SuggestionStatusFilter } from "./useSuggestionFilters";

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

  return useQuery<SuggestionListResponse>({
    queryKey: ["suggestions", status, kind, jurisdictionId, locale],
    queryFn: () =>
      fetchSuggestions({
        locale,
        status: statusParam(status),
        kind: kind ?? undefined,
        jurisdictionId: jurisdictionId ?? undefined,
      }),
    placeholderData: keepPreviousData,
  });
}
