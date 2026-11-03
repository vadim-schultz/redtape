import type { ListQueryController } from "../../../hooks/useListQueryState";
import type {
  CandidateFilterKey,
  CandidateSortKey,
  CatalogueFilterKey,
  CatalogueSortKey,
  TaskFilterKey,
  TaskSortKey,
} from "../types";

/** The URL-backed query controls of the crawler queue. */
export type TaskList = ListQueryController<TaskSortKey, TaskFilterKey>;

/** The URL-backed query controls of the documents list. */
export type CandidateList = ListQueryController<
  CandidateSortKey,
  CandidateFilterKey
>;

/** The URL-backed query controls of the catalogue index. */
export type CatalogueList = ListQueryController<
  CatalogueSortKey,
  CatalogueFilterKey
>;
