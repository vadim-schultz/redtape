import { Box, Text } from "@chakra-ui/react";
import { LuListTodo } from "react-icons/lu";

import EmptyStateCard from "../../../components/feedback/EmptyStateCard";
import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTask } from "../types";

import DiscoveryTasksSkeleton from "./DiscoveryTasksSkeleton";
import DiscoveryTasksTable from "./DiscoveryTasksTable";

export interface DiscoveryTasksQueryStatusProps {
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
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
  isLoading,
  isRefreshing,
  isError,
  onRetry,
  tasks,
}: DiscoveryTasksQueryStatusProps) {
  const { t } = useLocale();
  const count = tasks?.length ?? 0;
  const countKey = count === 1 ? "count_one" : "count_other";

  if (isLoading) return <DiscoveryTasksSkeleton />;
  if (isError) return <QueryError onRetry={onRetry} />;
  if (count === 0) return <EmptyTasksState />;

  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {t(`discovery_admin.tasks.${countKey}`, { count })}
      </Text>
      <Box
        aria-busy={isRefreshing}
        opacity={isRefreshing ? 0.6 : 1}
        transition="opacity 0.2s"
      >
        <DiscoveryTasksTable tasks={tasks ?? []} />
      </Box>
    </>
  );
}
