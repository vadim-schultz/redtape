import { Box, Text } from "@chakra-ui/react";
import { LuListTodo } from "react-icons/lu";

import EmptyStateCard from "../../../components/feedback/EmptyStateCard";
import QueryError from "../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTask } from "../types";

import DiscoveryTasksSkeleton from "./DiscoveryTasksSkeleton";
import DiscoveryTasksTable from "./DiscoveryTasksTable";

export interface DiscoveryTasksQueryStatusProps {
  status: QueryStatus;
  tasks: DiscoveryTask[] | undefined;
}

function EmptyTasksState() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuListTodo}
      title={t("discovery_admin.tasks.empty_title")}
      description={t("discovery_admin.tasks.empty_description")}
    />
  );
}

export default function DiscoveryTasksQueryStatus({
  status,
  tasks,
}: DiscoveryTasksQueryStatusProps) {
  const { t } = useLocale();
  const count = tasks?.length ?? 0;
  const countKey = count === 1 ? "count_one" : "count_other";

  if (status.isLoading) return <DiscoveryTasksSkeleton />;
  if (status.isError) return <QueryError onRetry={status.onRetry} />;
  if (count === 0) return <EmptyTasksState />;

  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {t(`discovery_admin.tasks.${countKey}`, { count })}
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
