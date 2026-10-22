import { Box, Text } from "@chakra-ui/react";
import { Fragment, type ReactNode } from "react";

import QueryError from "./QueryError";
import type { QueryStatus } from "./queryStatus";

export interface QueryStatusSlots<T> {
  getKey: (item: T) => string;
  renderItem: (item: T) => ReactNode;
  renderSkeleton: () => ReactNode;
  renderEmpty: () => ReactNode;
  countLabel: (count: number) => string;
}

export interface QueryStatusViewProps<T> {
  status: QueryStatus;
  items: T[] | undefined;
  slots: QueryStatusSlots<T>;
}

interface PopulatedListProps<T> {
  items: T[];
  isRefreshing: boolean;
  slots: QueryStatusSlots<T>;
}

function PopulatedList<T>({
  items,
  isRefreshing,
  slots,
}: PopulatedListProps<T>) {
  return (
    <>
      <Box data-testid="query-status-count-row" mb={2}>
        <Text data-testid="query-status-count" color="muted" fontSize="sm">
          {slots.countLabel(items.length)}
        </Text>
      </Box>
      <Box
        display="flex"
        flexDirection="column"
        gap={3}
        aria-busy={isRefreshing}
        opacity={isRefreshing ? 0.6 : 1}
        transition="opacity 0.2s"
      >
        {items.map((item) => (
          <Fragment key={slots.getKey(item)}>{slots.renderItem(item)}</Fragment>
        ))}
      </Box>
    </>
  );
}

function renderContent<T>({ status, items, slots }: QueryStatusViewProps<T>) {
  if (status.isLoading) return slots.renderSkeleton();
  if (status.isError) return <QueryError onRetry={status.onRetry} />;
  if ((items?.length ?? 0) === 0) return slots.renderEmpty();

  return (
    <PopulatedList
      items={items ?? []}
      isRefreshing={status.isRefreshing}
      slots={slots}
    />
  );
}

/** Shared loading/error/empty/populated states for a filtered, refetchable list. */
export default function QueryStatusView<T>(props: QueryStatusViewProps<T>) {
  return <>{renderContent(props)}</>;
}
