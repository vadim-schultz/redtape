import {
  useListQueryState,
  type ListQueryController,
} from "../../../hooks/useListQueryState";
import { CATALOGUE_LIST_SPEC } from "../services/catalogueListQuery";
import type { CatalogueFilterKey, CatalogueSortKey } from "../types";

/** The URL-backed query controls of the catalogue index. */
export type CatalogueList = ListQueryController<
  CatalogueSortKey,
  CatalogueFilterKey
>;

/** Search, filter, sort and page of the catalogue index, read from and written to the URL. */
export function useCatalogueListState(): CatalogueList {
  return useListQueryState(CATALOGUE_LIST_SPEC);
}
