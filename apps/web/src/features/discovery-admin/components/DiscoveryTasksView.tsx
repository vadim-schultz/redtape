import { Box, VStack } from "@chakra-ui/react";

import type { DiscoveryTask } from "../types";
import type { DiscoveryTaskFilters as DiscoveryTaskFiltersState } from "../hooks/useDiscoveryTaskFilters";

import DiscoveryTaskFilters from "./DiscoveryTaskFilters";
import DiscoveryTasksQueryStatus from "./DiscoveryTasksQueryStatus";

export interface DiscoveryTasksViewProps {
  filters: DiscoveryTaskFiltersState;
  tasks: DiscoveryTask[] | undefined;
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
}

export default function DiscoveryTasksView({
  filters,
  tasks,
  isLoading,
  isRefreshing,
  isError,
  error,
  onRetry,
}: DiscoveryTasksViewProps) {
  return (
    <VStack align="stretch" gap={4}>
      <DiscoveryTaskFilters filters={filters} />
      <Box>
        <DiscoveryTasksQueryStatus
          isLoading={isLoading}
          isRefreshing={isRefreshing}
          isError={isError}
          error={error}
          onRetry={onRetry}
          tasks={tasks}
        />
      </Box>
    </VStack>
  );
}
