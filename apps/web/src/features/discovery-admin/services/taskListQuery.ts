import {
  oneOfFilter,
  type ListQuerySpec,
  type ListQueryState,
} from "../../../services/listQuery";
import type { TaskFilterKey, TaskSortKey } from "../types";
import {
  DISCOVERY_SOURCES,
  TASK_KINDS,
  TASK_STATUSES,
} from "../types/listValues";

export type { TaskFilterKey, TaskSortKey };
export type TaskListQuery = ListQueryState<TaskSortKey, TaskFilterKey>;

const SORT_KEYS = [
  "target",
  "kind",
  "status",
  "source",
  "priority",
  "attempts",
] as const satisfies readonly TaskSortKey[];

/** Mirrors the API allowlist; values the API would refuse never reach a request or the URL state. */
export const TASK_LIST_SPEC: ListQuerySpec<TaskSortKey, TaskFilterKey> = {
  sortKeys: SORT_KEYS,
  filters: {
    status: oneOfFilter(TASK_STATUSES),
    source: oneOfFilter(DISCOVERY_SOURCES),
    kind: oneOfFilter(TASK_KINDS),
  },
  defaultLimit: 20,
  maxLimit: 100,
};
