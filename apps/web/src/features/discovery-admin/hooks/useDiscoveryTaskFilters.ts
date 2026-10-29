import { useCallback, useMemo, useState } from "react";

import type {
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
} from "../types";

export const TASKS_PAGE_SIZE = 20;

type FilterValues = {
  status: DiscoveryTaskStatus;
  source: DiscoverySource | null;
  kind: DiscoveryTaskKind | null;
};

export type DiscoveryTaskFilters = FilterValues & {
  offset: number;
  limit: number;
  setStatus: (status: DiscoveryTaskStatus) => void;
  setSource: (source: DiscoverySource | null) => void;
  setKind: (kind: DiscoveryTaskKind | null) => void;
  setOffset: (offset: number) => void;
};

const INITIAL: FilterValues = { status: "pending", source: null, kind: null };

/** Local filter and paging state of the crawler queue; a filter change returns to the first page. */
export function useDiscoveryTaskFilters(): DiscoveryTaskFilters {
  const [values, setValues] = useState<FilterValues>(INITIAL);
  const [offset, setOffset] = useState(0);

  const refilter = useCallback((patch: Partial<FilterValues>) => {
    setValues((current) => ({ ...current, ...patch }));
    setOffset(0);
  }, []);

  return useMemo(
    () => ({
      ...values,
      offset,
      limit: TASKS_PAGE_SIZE,
      setStatus: (status) => refilter({ status }),
      setSource: (source) => refilter({ source }),
      setKind: (kind) => refilter({ kind }),
      setOffset,
    }),
    [values, offset, refilter],
  );
}
