import { Skeleton, Stack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import QueryError from "../../feedback/QueryError";
import type { TableState } from "./tableState";
import type { DataTableStates } from "./types";

function LoadingRows() {
  return (
    <Stack gap={2} aria-busy="true">
      <Skeleton height="5" />
      <Skeleton height="5" />
      <Skeleton height="5" />
    </Stack>
  );
}

export interface DataTableStateViewProps {
  state: Exclude<TableState, "populated">;
  states: DataTableStates;
}

const SLOTS: Record<
  DataTableStateViewProps["state"],
  (states: DataTableStates) => ReactNode
> = {
  loading: ({ loading }) => loading ?? <LoadingRows />,
  empty: ({ empty }) => empty,
  error: ({ error, status }) =>
    error ?? <QueryError onRetry={() => status?.onRetry()} />,
};

/** The slot for a non-populated state, falling back to the shared default. */
export default function DataTableStateView({
  state,
  states,
}: DataTableStateViewProps) {
  return <>{SLOTS[state](states)}</>;
}
