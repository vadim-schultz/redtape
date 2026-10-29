import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import {
  parseListUrl,
  serializeListUrl,
  withFilter,
  withOffset,
  withSearch,
  withSort,
  type FilterValue,
  type ListQuerySpec,
  type ListQueryState,
  type SortChange,
} from "../services/listQuery";

export interface ListQueryController<
  SortKey extends string,
  FilterKey extends string,
> {
  state: ListQueryState<SortKey, FilterKey>;
  setSort: (sort: SortChange<SortKey>) => void;
  setSearch: (search: string) => void;
  setFilter: (key: FilterKey, value: FilterValue | undefined) => void;
  setOffset: (offset: number) => void;
}

/** URL search params are the single source of truth for a list's query; every write is validated by `spec`. */
export function useListQueryState<
  SortKey extends string,
  FilterKey extends string,
>(
  spec: ListQuerySpec<SortKey, FilterKey>,
): ListQueryController<SortKey, FilterKey> {
  const [params, setParams] = useSearchParams();
  const state = useMemo(() => parseListUrl(params, spec), [params, spec]);

  const update = useCallback(
    (
      change: (
        current: ListQueryState<SortKey, FilterKey>,
      ) => ListQueryState<SortKey, FilterKey>,
    ) =>
      setParams((prev) =>
        serializeListUrl(change(parseListUrl(prev, spec)), spec, prev),
      ),
    [setParams, spec],
  );

  return useMemo(
    () => ({
      state,
      setSort: (sort) => update((current) => withSort(current, sort)),
      setSearch: (search) => update((current) => withSearch(current, search)),
      setFilter: (key, value) =>
        update((current) => withFilter(current, key, value)),
      setOffset: (offset) => update((current) => withOffset(current, offset)),
    }),
    [state, update],
  );
}
