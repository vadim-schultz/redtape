import {
  useQuery,
  type QueryKey,
  type UseQueryOptions,
  type UseQueryResult,
} from "@tanstack/react-query";

export type ApiQueryOptions<T> = Omit<
  UseQueryOptions<T, Error, T, QueryKey>,
  "queryKey" | "queryFn"
>;

/** Shared GET-query wrapper: feature hooks pass a key from `queryKeys` and a service call. */
export function useApiQuery<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  options?: ApiQueryOptions<T>,
): UseQueryResult<T> {
  return useQuery<T, Error, T, QueryKey>({ queryKey, queryFn, ...options });
}
