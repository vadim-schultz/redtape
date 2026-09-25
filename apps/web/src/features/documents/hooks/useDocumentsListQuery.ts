import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchDocuments } from "../services/documentsApi";
import type { DocumentListResponse } from "../types";

export interface DocumentsListFilters {
  domains: string[];
  situations: string[];
}

export function useDocumentsListQuery(
  municipalityCode: string | null,
  { domains, situations }: DocumentsListFilters,
) {
  const { locale } = useLocale();

  return useQuery<DocumentListResponse>({
    queryKey: ["documents", municipalityCode, domains, situations, locale],
    queryFn: () =>
      fetchDocuments({ locale, municipalityCode, domains, situations }),
    placeholderData: keepPreviousData,
  });
}
