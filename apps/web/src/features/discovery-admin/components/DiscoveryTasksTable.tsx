import { Table } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../suggestions/utils/formatRelativeTime";
import type { DiscoveryTask } from "../types";

function formatLeaseExpiry(
  leaseExpiresAt: string | null,
  t: (key: string) => string,
): string {
  if (!leaseExpiresAt) return t("discovery_admin.tasks.lease_none");
  return formatRelativeTime(leaseExpiresAt);
}

export default function DiscoveryTasksTable({
  tasks,
}: {
  tasks: DiscoveryTask[];
}) {
  const { t } = useLocale();

  return (
    <Table.Root size="sm" variant="line">
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>
            {t("discovery_admin.tasks.col_target")}
          </Table.ColumnHeader>
          <Table.ColumnHeader>
            {t("discovery_admin.tasks.col_status")}
          </Table.ColumnHeader>
          <Table.ColumnHeader>
            {t("discovery_admin.tasks.col_source")}
          </Table.ColumnHeader>
          <Table.ColumnHeader>
            {t("discovery_admin.tasks.col_priority")}
          </Table.ColumnHeader>
          <Table.ColumnHeader>
            {t("discovery_admin.tasks.col_lease")}
          </Table.ColumnHeader>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {tasks.map((task) => (
          <Table.Row key={task.id}>
            <Table.Cell>{task.target_url}</Table.Cell>
            <Table.Cell>{task.status}</Table.Cell>
            <Table.Cell>{task.source}</Table.Cell>
            <Table.Cell>{task.priority}</Table.Cell>
            <Table.Cell>
              {formatLeaseExpiry(task.lease_expires_at, t)}
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}
