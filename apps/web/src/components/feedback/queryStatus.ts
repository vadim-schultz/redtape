/** Query state that views render: one object instead of five loose props. */
export interface QueryStatus {
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
}

/** The slice of a TanStack query that `toQueryStatus` reads. */
export interface QueryLike {
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/** Map a query to the `QueryStatus` its view renders. */
export function toQueryStatus(query: QueryLike): QueryStatus {
  return {
    isLoading: query.isLoading,
    isRefreshing: query.isFetching && !query.isLoading,
    isError: query.isError,
    error: query.error,
    onRetry: () => void query.refetch(),
  };
}
