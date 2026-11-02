import { useMemo } from "react";

import {
  useListQueryState,
  type ListQueryController,
} from "../../../hooks/useListQueryState";
import type { SortChange, SortOrder } from "../../../services/listQuery";
import { DOCUMENT_LIST_SPEC } from "../services/documentListQuery";
import type { DocumentSortKey } from "../types";

/** The sort the API applies when none is sent, and the one the controls show. */
export const DEFAULT_SORT = {
  sortBy: "confidence",
  sortOrder: "desc",
} as const satisfies { sortBy: DocumentSortKey; sortOrder: SortOrder };

type Sort = { sortBy: DocumentSortKey; sortOrder: SortOrder };

/** The URL-backed search, sort and page controls of the documents list. */
export interface DocumentList extends ListQueryController<
  DocumentSortKey,
  never
> {
  /** The sort in effect: the URL's, or the default when the URL names none. */
  sort: Sort;
}

function isDefaultSort({ sortBy, sortOrder }: SortChange<DocumentSortKey>) {
  return (
    sortBy === DEFAULT_SORT.sortBy &&
    (sortOrder ?? "asc") === DEFAULT_SORT.sortOrder
  );
}

/** Search, sort and page of the documents list, read from and written to the URL. */
export function useDocumentListState(): DocumentList {
  const list = useListQueryState(DOCUMENT_LIST_SPEC);
  const { sortBy, sortOrder } = list.state;

  return useMemo(
    () => ({
      ...list,
      sort: {
        sortBy: sortBy ?? DEFAULT_SORT.sortBy,
        sortOrder: sortOrder ?? DEFAULT_SORT.sortOrder,
      },
      setSort: (sort) => list.setSort(isDefaultSort(sort) ? {} : sort),
    }),
    [list, sortBy, sortOrder],
  );
}
