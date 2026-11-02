import { keepPreviousData } from "@tanstack/react-query";

import { queryKeys } from "../../../app/queryKeys";
import type { CatalogueListQuery } from "../services/catalogueListQuery";
import { listDiscoveryCatalogue } from "../services/discoveryAdminApi";
import type { CatalogueListResponse } from "../types";
import { useAdminQuery } from "./useAdminQuery";

/** One page of the catalogue index for the typed query state. */
export function useDiscoveryCatalogueQuery(query: CatalogueListQuery) {
  return useAdminQuery<CatalogueListResponse>(
    (locale) => queryKeys.discoveryAdmin.catalogue(query, locale),
    (auth) => listDiscoveryCatalogue(auth, query),
    { placeholderData: keepPreviousData },
  );
}
