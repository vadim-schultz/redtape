import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
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

  return useApiQuery<DocumentListResponse>(
    queryKeys.documents.list(municipalityCode, domains, situations, locale),
    () => fetchDocuments({ locale, municipalityCode, domains, situations }),
    { placeholderData: keepPreviousData },
  );
}
