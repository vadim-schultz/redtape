import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchDocumentDetail } from "../services/documentsApi";
import type { DocumentDetail } from "../types";

export function useDocumentDetailQuery(id?: string) {
  const { locale } = useLocale();

  return useQuery<DocumentDetail>({
    queryKey: ["document_detail", id],
    enabled: !!id,
    queryFn: () => fetchDocumentDetail({ locale, id: id as string }),
  });
}
