import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchDocuments } from "../services/documentsApi";
import type { DocumentListRequest, DocumentListResponse } from "../types";

/** One page of the documents list; the previous page stays while the next loads. */
export function useDocumentsListQuery(request: DocumentListRequest) {
  const { locale } = useLocale();

  return useApiQuery<DocumentListResponse>(
    queryKeys.documents.list(request, locale),
    () => fetchDocuments({ locale, request }),
    { placeholderData: keepPreviousData },
  );
}
