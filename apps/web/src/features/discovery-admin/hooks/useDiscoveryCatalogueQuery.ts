import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { listDiscoveryCatalogue } from "../services/discoveryAdminApi";
import type { CatalogueListResponse } from "../types";

/** Paginated catalogue rows for the admin index page. */
export function useDiscoveryCatalogueQuery() {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  return useQuery<CatalogueListResponse>({
    queryKey: ["discovery-admin", "catalogue", locale],
    queryFn: () =>
      listDiscoveryCatalogue({
        locale,
        accessToken: accessToken!,
        limit: 50,
      }),
    enabled: Boolean(accessToken),
    placeholderData: keepPreviousData,
  });
}
