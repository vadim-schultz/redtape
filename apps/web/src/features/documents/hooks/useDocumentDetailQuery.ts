import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchDocumentDetail } from "../services/documentsApi";
import type { DocumentDetail } from "../types";

export function useDocumentDetailQuery(id?: string) {
  const { locale } = useLocale();

  return useApiQuery<DocumentDetail>(
    queryKeys.documents.detail(id),
    () => fetchDocumentDetail({ locale, id: id as string }),
    { enabled: !!id },
  );
}
