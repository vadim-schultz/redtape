import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import { listDiscoveryCatalogue } from "../services/discoveryAdminApi";
import type { CatalogueListResponse } from "../types";

/** Paginated catalogue rows for the admin index page. */
export function useDiscoveryCatalogueQuery() {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useApiQuery<CatalogueListResponse>(
    queryKeys.discoveryAdmin.catalogue(locale),
    () =>
      listDiscoveryCatalogue({
        locale,
        accessToken: accessToken!,
        limit: 50,
      }),
    { enabled: Boolean(accessToken), placeholderData: keepPreviousData },
  );
}
