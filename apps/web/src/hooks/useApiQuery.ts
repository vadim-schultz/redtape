import {
  useQuery,
  type QueryKey,
  type SkipToken,
  type UseQueryOptions,
  type UseQueryResult,
} from "@tanstack/react-query";

export type ApiQueryOptions<T> = Omit<
  UseQueryOptions<T, Error, T, QueryKey>,
  "queryKey" | "queryFn"
>;

/** Shared GET-query wrapper: feature hooks pass a key from `queryKeys` and a service call, or `skipToken` to stay idle. */
export function useApiQuery<T>(
  queryKey: QueryKey,
  queryFn: (() => Promise<T>) | SkipToken,
  options?: ApiQueryOptions<T>,
): UseQueryResult<T> {
  return useQuery<T, Error, T, QueryKey>({ queryKey, queryFn, ...options });
}
