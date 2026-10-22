import { Box, VStack } from "@chakra-ui/react";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import type { DiscoveryTask } from "../types";
import type { DiscoveryTaskFilters as DiscoveryTaskFiltersState } from "../hooks/useDiscoveryTaskFilters";

import DiscoveryTaskFilters from "./DiscoveryTaskFilters";
import DiscoveryTasksQueryStatus from "./DiscoveryTasksQueryStatus";

export interface DiscoveryTasksViewProps {
  filters: DiscoveryTaskFiltersState;
  tasks: DiscoveryTask[] | undefined;
  status: QueryStatus;
}

export default function DiscoveryTasksView({
  filters,
  tasks,
  status,
}: DiscoveryTasksViewProps) {
  return (
    <VStack align="stretch" gap={4}>
      <DiscoveryTaskFilters filters={filters} />
      <Box>
        <DiscoveryTasksQueryStatus status={status} tasks={tasks} />
      </Box>
    </VStack>
  );
}
