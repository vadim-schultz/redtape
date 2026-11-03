import {
  defineListSpec,
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import {
  DISCOVERY_SOURCES,
  TASK_KINDS,
  TASK_SORT_KEYS,
  TASK_STATUSES,
  type TaskFilterKey,
  type TaskSortKey,
} from "../types";

export type { TaskFilterKey, TaskSortKey };
export type TaskListQuery = ListQueryState<TaskSortKey, TaskFilterKey>;

/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const TASK_LIST_SPEC: ListQuerySpec<TaskSortKey, TaskFilterKey> =
  defineListSpec({
    sortKeys: TASK_SORT_KEYS,
    filters: {
      status: oneOfFilter(TASK_STATUSES),
      source: oneOfFilter(DISCOVERY_SOURCES),
      kind: oneOfFilter(TASK_KINDS),
    },
  });
