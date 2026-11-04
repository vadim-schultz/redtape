import { LuListTodo } from "react-icons/lu";

import { toTableQuery } from "../../../hooks/toTableQuery";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { TaskList } from "../types/listControllers";
import type { DiscoveryTaskListResponse } from "../types";
import { taskColumns } from "./columns/taskColumns";
import DiscoveryDataTable from "./DiscoveryDataTable";

const NAMESPACE = "discovery_admin.tasks";
const COPY = { namespace: NAMESPACE, icon: LuListTodo };

export interface DiscoveryTasksTableProps {
  page: DiscoveryTaskListResponse | undefined;
  status: QueryStatus;
  list: TaskList;
}

/** Crawler queue rows in the shared table: header sort and filters, response total and server paging. */
export default function DiscoveryTasksTable({
  page,
  status,
  list,
}: DiscoveryTasksTableProps) {
  const locale = useLocale();

  return (
    <DiscoveryDataTable
      table={{
        label: locale.t(`${NAMESPACE}.table_label`),
        columns: taskColumns(locale),
        getKey: (task) => task.id,
        query: toTableQuery(list),
      }}
      page={page}
      status={status}
      onOffsetChange={list.setOffset}
      copy={COPY}
    />
  );
}
