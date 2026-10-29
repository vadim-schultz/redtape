import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import type { CatalogueListQuery } from "../services/catalogueListQuery";
import { listDiscoveryCatalogue } from "../services/discoveryAdminApi";
import type { CatalogueListResponse } from "../types";

/** One page of the catalogue index for the typed query state. */
export function useDiscoveryCatalogueQuery(query: CatalogueListQuery) {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<CatalogueListResponse>(
    queryKeys.discoveryAdmin.catalogue(query, locale),
    () => listDiscoveryCatalogue({ locale, accessToken: accessToken!, query }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}
