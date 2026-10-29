import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import { formatRelativeTime } from "../../../suggestions/utils/formatRelativeTime";
import {
  DISCOVERY_SOURCES,
  TASK_KINDS,
  TASK_STATUSES,
} from "../../types/listValues";
import type { DiscoveryTask, TaskFilterKey, TaskSortKey } from "../../types";
import { formatRetryAfter } from "../../utils/formatRetryAfter";
import TaskStatusCell from "./cells/TaskStatusCell";
import { headerLabels, type ColumnContext } from "./columnContext";
import { plainOptions } from "./filterOptions";
import LongText from "./LongText";

/** Rendered action-free columns of the queue; retry and lease are timestamps without a server sort. */
export type TaskColumn = DataTableColumn<
  DiscoveryTask,
  TaskSortKey,
  TaskFilterKey
>;

/** Columns of the crawler queue. */
export function taskColumns(context: ColumnContext): TaskColumn[] {
  const { locale, t } = context;
  const header = headerLabels(context, "discovery_admin.tasks");
  const none = t("discovery_admin.tasks.retry_none");
  const filterOf = (key: TaskFilterKey, values: readonly string[]) => ({
    key,
    operators: ["eq"] as const,
    label: t(`discovery_admin.tasks.filter_${key}`),
    options: plainOptions(values),
  });
  return [
    {
      key: "target",
      header: header("target"),
      canSort: "target",
      render: (task) => <LongText>{task.target_url}</LongText>,
    },
    {
      key: "kind",
      header: header("kind"),
      canSort: "kind",
      filter: filterOf("kind", TASK_KINDS),
      render: (task) => task.kind,
    },
    {
      key: "status",
      header: header("status"),
      canSort: "status",
      filter: filterOf("status", TASK_STATUSES),
      render: (task) => <TaskStatusCell task={task} />,
    },
    {
      key: "source",
      header: header("source"),
      canSort: "source",
      filter: filterOf("source", DISCOVERY_SOURCES),
      render: (task) => task.source,
    },
    {
      key: "priority",
      header: header("priority"),
      align: "end",
      canSort: "priority",
      render: (task) => task.priority,
    },
    {
      key: "attempts",
      header: header("attempts"),
      align: "end",
      canSort: "attempts",
      render: (task) => task.attempt_count,
    },
    {
      key: "retry",
      header: header("retry"),
      render: (task) => formatRetryAfter(task.not_before, locale) ?? none,
    },
    {
      key: "lease",
      header: header("lease"),
      render: (task) =>
        task.lease_expires_at
          ? formatRelativeTime(task.lease_expires_at, locale)
          : t("discovery_admin.tasks.lease_none"),
    },
  ];
}
