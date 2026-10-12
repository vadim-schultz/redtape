import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchEvidenceForSuggestion } from "../services/evidenceApi";

export function useEvidenceQuery(suggestionId: string | undefined) {
  const { locale } = useLocale();

  return useQuery({
    queryKey: ["evidence", suggestionId, locale],
    queryFn: () => fetchEvidenceForSuggestion(suggestionId!, locale),
    enabled: Boolean(suggestionId),
    refetchOnWindowFocus: false,
    retry: false,
  });
}
