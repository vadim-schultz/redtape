import { VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import type { DiscoveryTaskListResponse } from "../types";
import type { DiscoveryTaskFilters as DiscoveryTaskFiltersState } from "../hooks/useDiscoveryTaskFilters";

import DiscoveryTaskFilters from "./DiscoveryTaskFilters";
import DiscoveryTasksTable from "./DiscoveryTasksTable";

export interface DiscoveryTasksViewProps {
  filters: DiscoveryTaskFiltersState;
  page: DiscoveryTaskListResponse | undefined;
  status: QueryStatus;
}

/** Crawler queue filters above the shared tasks table. */
export default function DiscoveryTasksView({
  filters,
  page,
  status,
}: DiscoveryTasksViewProps) {
  return (
    <VStack align="stretch" gap={4}>
      <DiscoveryTaskFilters filters={filters} />
      <DiscoveryTasksTable
        page={page}
        status={status}
        onOffsetChange={filters.setOffset}
      />
    </VStack>
  );
}
