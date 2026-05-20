import { useQuery } from '@tanstack/react-query';

import { useLocale } from '../../../contexts/LocaleContext';
import { fetchDocuments } from '../services/documentsApi';
import type { DocumentListResponse } from '../types';

export function useDocumentsListQuery(municipalityCode: string | null) {
  const { locale } = useLocale();

  return useQuery<DocumentListResponse>({
    queryKey: ['documents', municipalityCode, locale],
    queryFn: () => fetchDocuments({ locale, municipalityCode }),
  });
}

