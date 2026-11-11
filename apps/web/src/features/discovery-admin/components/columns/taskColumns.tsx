import type { DataTableColumn } from "../../../../components/data-display/DataTable";
import TruncatedText from "../../../../components/data-display/TruncatedText";
import { DISCOVERY_SOURCES, TASK_KINDS, TASK_STATUSES } from "../../types";
import type { DiscoveryTask, TaskFilterKey, TaskSortKey } from "../../types";
import {
  formatRelativeTime,
  formatTimeUntil,
} from "../../../../utils/format/formatRelativeTime";
import { translateOrRaw } from "../../utils/translateOrRaw";
import TaskStatusCell from "./cells/TaskStatusCell";
import { headerLabels, type ColumnContext } from "./columnContext";
import { filterCapability } from "./filterCapability";
import { enumOptions, plainOptions } from "./filterOptions";

/** Width at which the target URL is clipped. */
const TARGET_MAX_WIDTH = "24rem";

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
  return [
    {
      key: "target",
      header: header("target"),
      canSort: "target",
      maxWidth: TARGET_MAX_WIDTH,
      render: (task) => (
        <TruncatedText maxWidth={TARGET_MAX_WIDTH}>
          {task.target_url}
        </TruncatedText>
      ),
    },
    {
      key: "kind",
      header: header("kind"),
      canSort: "kind",
      filter: filterCapability({
        key: "kind",
        label: t("discovery_admin.tasks.filter_kind"),
        options: plainOptions(TASK_KINDS),
      }),
      render: (task) => task.kind,
    },
    {
      key: "status",
      header: header("status"),
      canSort: "status",
      filter: filterCapability({
        key: "status",
        label: t("discovery_admin.tasks.filter_status"),
        options: enumOptions(t, "task_status", TASK_STATUSES),
      }),
      render: (task) => <TaskStatusCell task={task} />,
    },
    {
      key: "source",
      header: header("source"),
      canSort: "source",
      filter: filterCapability({
        key: "source",
        label: t("discovery_admin.tasks.filter_source"),
        options: enumOptions(t, "source", DISCOVERY_SOURCES),
      }),
      render: (task) =>
        translateOrRaw(
          t,
          `discovery_admin.values.source_${task.source}`,
          task.source,
        ),
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
      render: (task) => formatTimeUntil(task.not_before, locale) ?? none,
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
