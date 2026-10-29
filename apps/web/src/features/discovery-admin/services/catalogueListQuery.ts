import {
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import type { CatalogueFilterKey, CatalogueSortKey } from "../types";
import { DISCOVERY_SOURCES } from "../types/listValues";

export type { CatalogueFilterKey, CatalogueSortKey };
export type CatalogueListQuery = ListQueryState<
  CatalogueSortKey,
  CatalogueFilterKey
>;

const SORT_KEYS = [
  "external_id",
  "source",
  "stage",
] as const satisfies readonly CatalogueSortKey[];

/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const CATALOGUE_LIST_SPEC: ListQuerySpec<
  CatalogueSortKey,
  CatalogueFilterKey
> = {
  sortKeys: SORT_KEYS,
  filters: { source: oneOfFilter(DISCOVERY_SOURCES) },
  defaultLimit: 20,
  maxLimit: 100,
};
