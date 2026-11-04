import { VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import ListSearchBox from "../../../components/data-display/ListSearchBox";
import { useLocale } from "../../../contexts/LocaleContext";
import type { TaskList } from "../types/listControllers";
import type { DiscoveryTaskListResponse } from "../types";
import DiscoveryTasksTable from "./DiscoveryTasksTable";

export interface DiscoveryTasksViewProps {
  list: TaskList;
  page: DiscoveryTaskListResponse | undefined;
  status: QueryStatus;
}

/** Target search above the shared tasks table, whose header carries sort and filters. */
export default function DiscoveryTasksView({
  list,
  page,
  status,
}: DiscoveryTasksViewProps) {
  const { t } = useLocale();

  return (
    <VStack align="stretch" gap={4}>
      <ListSearchBox
        value={list.state.search}
        copy={{ label: t("discovery_admin.tasks.filter_search") }}
        onSearch={list.setSearch}
      />
      <DiscoveryTasksTable page={page} status={status} list={list} />
    </VStack>
  );
}
