import { useCallback, useMemo, useState } from "react";

import type {
  DiscoveryCandidateSort,
  DiscoveryMentionRole,
  DiscoverySource,
} from "../types";

export const DOCUMENTS_PAGE_SIZE = 20;

type FilterValues = {
  q: string;
  minMentions: number | null;
  role: DiscoveryMentionRole | null;
  source: DiscoverySource | null;
  sort: DiscoveryCandidateSort;
};

export type DiscoveryDocumentFilters = FilterValues & {
  offset: number;
  limit: number;
  /** Change one or more filters; the list returns to its first page. */
  setFilters: (patch: Partial<FilterValues>) => void;
  setOffset: (offset: number) => void;
};

const INITIAL: FilterValues = {
  q: "",
  minMentions: null,
  role: null,
  source: null,
  sort: "mentions_desc",
};

/** Local search, filter, sort and paging state of the documents list. */
export function useDiscoveryDocumentFilters(): DiscoveryDocumentFilters {
  const [values, setValues] = useState<FilterValues>(INITIAL);
  const [offset, setOffset] = useState(0);

  const setFilters = useCallback((patch: Partial<FilterValues>) => {
    setValues((current) => ({ ...current, ...patch }));
    setOffset(0);
  }, []);

  return useMemo(
    () => ({
      ...values,
      offset,
      limit: DOCUMENTS_PAGE_SIZE,
      setFilters,
      setOffset,
    }),
    [values, offset, setFilters],
  );
}
