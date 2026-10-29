import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import { formatRelativeTime } from "../../../suggestions/utils/formatRelativeTime";
import type { DiscoveryTask } from "../../types";
import { formatRetryAfter } from "../../utils/formatRetryAfter";
import TaskStatusCell from "./cells/TaskStatusCell";
import { headerLabels, type ColumnContext } from "./columnContext";
import LongText from "./LongText";

/** The tasks API has no sort or filter contract yet, so no task column declares one. */
export type TaskColumn = DataTableColumn<DiscoveryTask, never, never>;

/** Columns of the crawler queue. */
export function taskColumns(context: ColumnContext): TaskColumn[] {
  const { locale, t } = context;
  const header = headerLabels(context, "discovery_admin.tasks");
  const none = t("discovery_admin.tasks.retry_none");
  return [
    {
      key: "target",
      header: header("target"),
      render: (task) => <LongText>{task.target_url}</LongText>,
    },
    { key: "kind", header: header("kind"), render: (task) => task.kind },
    {
      key: "status",
      header: header("status"),
      render: (task) => <TaskStatusCell task={task} />,
    },
    { key: "source", header: header("source"), render: (task) => task.source },
    {
      key: "priority",
      header: header("priority"),
      render: (task) => task.priority,
    },
    {
      key: "attempts",
      header: header("attempts"),
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
