import {
  defineListSpec,
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import {
  CATALOGUE_SORT_KEYS,
  DISCOVERY_SOURCES,
  PIPELINE_STAGES,
  type CatalogueFilterKey,
  type CatalogueSortKey,
} from "../types";

export type { CatalogueFilterKey, CatalogueSortKey };
export type CatalogueListQuery = ListQueryState<
  CatalogueSortKey,
  CatalogueFilterKey
>;

/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const CATALOGUE_LIST_SPEC: ListQuerySpec<
  CatalogueSortKey,
  CatalogueFilterKey
> = defineListSpec({
  sortKeys: CATALOGUE_SORT_KEYS,
  filters: {
    source: oneOfFilter(DISCOVERY_SOURCES),
    stage: oneOfFilter(PIPELINE_STAGES),
  },
});
