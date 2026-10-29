import {
  useListQueryState,
  type ListQueryController,
} from "../../../hooks/useListQueryState";
import { TASK_LIST_SPEC } from "../services/taskListQuery";
import type { TaskFilterKey, TaskSortKey } from "../types";

/** The URL-backed query controls of the crawler queue. */
export type TaskList = ListQueryController<TaskSortKey, TaskFilterKey>;

/** Search, filter, sort and page of the crawler queue, read from and written to the URL. */
export function useTaskListState(): TaskList {
  return useListQueryState(TASK_LIST_SPEC);
}
