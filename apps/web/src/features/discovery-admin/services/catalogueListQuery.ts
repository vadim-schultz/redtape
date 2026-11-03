import {
  defineListSpec,
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import type { CatalogueFilterKey, CatalogueSortKey } from "../types";
import { DISCOVERY_SOURCES, PIPELINE_STAGES } from "../types/listValues";

export type { CatalogueFilterKey, CatalogueSortKey };
export type CatalogueListQuery = ListQueryState<
  CatalogueSortKey,
  CatalogueFilterKey
>;

const SORT_KEYS = [
  "external_id",
  "title",
  "source",
  "stage",
] as const satisfies readonly CatalogueSortKey[];

/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const CATALOGUE_LIST_SPEC: ListQuerySpec<
  CatalogueSortKey,
  CatalogueFilterKey
> = defineListSpec({
  sortKeys: SORT_KEYS,
  filters: {
    source: oneOfFilter(DISCOVERY_SOURCES),
    stage: oneOfFilter(PIPELINE_STAGES),
  },
});
