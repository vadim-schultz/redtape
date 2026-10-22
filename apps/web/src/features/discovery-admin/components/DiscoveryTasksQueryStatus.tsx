import { Box, Text } from "@chakra-ui/react";
import { LuListTodo } from "react-icons/lu";

import NamespacedEmptyState from "../../../components/feedback/NamespacedEmptyState";
import QueryError from "../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useCountLabel } from "../../../components/feedback/useCountLabel";
import type { DiscoveryTask } from "../types";

import DiscoveryTasksSkeleton from "./DiscoveryTasksSkeleton";
import DiscoveryTasksTable from "./DiscoveryTasksTable";

export interface DiscoveryTasksQueryStatusProps {
  status: QueryStatus;
  tasks: DiscoveryTask[] | undefined;
}

const NAMESPACE = "discovery_admin.tasks";

export default function DiscoveryTasksQueryStatus({
  status,
  tasks,
}: DiscoveryTasksQueryStatusProps) {
  const countLabel = useCountLabel(NAMESPACE);
  const count = tasks?.length ?? 0;

  if (status.isLoading) return <DiscoveryTasksSkeleton />;
  if (status.isError) return <QueryError onRetry={status.onRetry} />;
  if (count === 0)
    return <NamespacedEmptyState namespace={NAMESPACE} icon={LuListTodo} />;

  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {countLabel(count)}
      </Text>
      <Box
        aria-busy={status.isRefreshing}
        opacity={status.isRefreshing ? 0.6 : 1}
        transition="opacity 0.2s"
      >
        <DiscoveryTasksTable tasks={tasks ?? []} />
      </Box>
    </>
  );
}
