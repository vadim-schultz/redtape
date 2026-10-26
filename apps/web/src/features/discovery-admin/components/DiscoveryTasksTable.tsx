import { Table } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../suggestions/utils/formatRelativeTime";
import type { DiscoveryTask } from "../types";
import { formatRetryAfter } from "../utils/formatRetryAfter";

const COLUMNS = [
  "target",
  "kind",
  "status",
  "source",
  "priority",
  "attempts",
  "retry",
  "lease",
];

function formatLeaseExpiry(
  leaseExpiresAt: string | null,
  locale: string,
  t: (key: string) => string,
): string {
  if (!leaseExpiresAt) return t("discovery_admin.tasks.lease_none");
  return formatRelativeTime(leaseExpiresAt, locale);
}

export default function DiscoveryTasksTable({
  tasks,
}: {
  tasks: DiscoveryTask[];
}) {
  const { locale, t } = useLocale();

  return (
    <Table.Root size="sm" variant="line">
      <Table.Header>
        <Table.Row>
          {COLUMNS.map((column) => (
            <Table.ColumnHeader key={column}>
              {t(`discovery_admin.tasks.col_${column}`)}
            </Table.ColumnHeader>
          ))}
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {tasks.map((task) => (
          <Table.Row key={task.id}>
            <Table.Cell>{task.target_url}</Table.Cell>
            <Table.Cell>{task.kind}</Table.Cell>
            <Table.Cell>{task.status}</Table.Cell>
            <Table.Cell>{task.source}</Table.Cell>
            <Table.Cell>{task.priority}</Table.Cell>
            <Table.Cell>{task.attempt_count}</Table.Cell>
            <Table.Cell>
              {formatRetryAfter(task.not_before, locale) ??
                t("discovery_admin.tasks.retry_none")}
            </Table.Cell>
            <Table.Cell>
              {formatLeaseExpiry(task.lease_expires_at, locale, t)}
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}
