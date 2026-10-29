import { LuListTodo } from "react-icons/lu";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTaskListResponse } from "../types";
import { taskColumns } from "./columns/taskColumns";
import DiscoveryDataTable from "./DiscoveryDataTable";

const NAMESPACE = "discovery_admin.tasks";
const COPY = { namespace: NAMESPACE, icon: LuListTodo };

export interface DiscoveryTasksTableProps {
  page: DiscoveryTaskListResponse | undefined;
  status: QueryStatus;
  onOffsetChange: (offset: number) => void;
}

/** Crawler queue rows in the shared table with the response total and server paging. */
export default function DiscoveryTasksTable({
  page,
  status,
  onOffsetChange,
}: DiscoveryTasksTableProps) {
  const locale = useLocale();

  return (
    <DiscoveryDataTable
      table={{
        label: locale.t(`${NAMESPACE}.table_label`),
        columns: taskColumns(locale),
        getKey: (task) => task.id,
      }}
      page={page}
      status={status}
      onOffsetChange={onOffsetChange}
      copy={COPY}
    />
  );
}
