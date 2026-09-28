import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchSuggestionDetail } from "../services/suggestionsApi";
import type { SuggestionRead } from "../types";

export function useSuggestionDetailQuery(id?: string) {
  const { locale } = useLocale();

  return useQuery<SuggestionRead>({
    queryKey: ["suggestion_detail", id],
    enabled: !!id,
    queryFn: () => fetchSuggestionDetail({ locale, id: id as string }),
  });
}
