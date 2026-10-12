import { Box, Text } from "@chakra-ui/react";
import { Fragment, type ReactNode } from "react";

import QueryError from "./QueryError";

export interface QueryStatusViewProps<T> {
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  items: T[] | undefined;
  getKey: (item: T) => string;
  renderItem: (item: T) => ReactNode;
  renderSkeleton: () => ReactNode;
  renderEmpty: () => ReactNode;
  countLabel: (count: number) => string;
}

function PopulatedList<T>({
  items,
  isRefreshing,
  getKey,
  renderItem,
  countLabel,
}: Pick<
  QueryStatusViewProps<T>,
  "items" | "isRefreshing" | "getKey" | "renderItem" | "countLabel"
> & { items: T[] }) {
  return (
    <>
      <Box data-testid="query-status-count-row" mb={2}>
        <Text data-testid="query-status-count" color="muted" fontSize="sm">
          {countLabel(items.length)}
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
          <Fragment key={getKey(item)}>{renderItem(item)}</Fragment>
        ))}
      </Box>
    </>
  );
}

function renderContent<T>(props: QueryStatusViewProps<T>) {
  const { isLoading, isError, onRetry, items, renderSkeleton, renderEmpty } =
    props;

  if (isLoading) return renderSkeleton();
  if (isError) return <QueryError onRetry={onRetry} />;
  if ((items?.length ?? 0) === 0) return renderEmpty();

  return (
    <PopulatedList
      items={items ?? []}
      isRefreshing={props.isRefreshing}
      getKey={props.getKey}
      renderItem={props.renderItem}
      countLabel={props.countLabel}
    />
  );
}

/** Shared loading/error/empty/populated states for a filtered, refetchable list. */
export default function QueryStatusView<T>(props: QueryStatusViewProps<T>) {
  return <>{renderContent(props)}</>;
}
