import type { ListQuerySpec } from "../../../services/listQuery";
import type { DocumentSortKey } from "../types";

const SORT_KEYS = [
  "confidence",
  "title",
  "created_at",
] as const satisfies readonly DocumentSortKey[];

/** Search, sort and page of the documents list; the taxonomy chips are not part of the spec. */
export const DOCUMENT_LIST_SPEC: ListQuerySpec<DocumentSortKey, never> = {
  sortKeys: SORT_KEYS,
  filters: {},
  defaultLimit: 20,
  maxLimit: 100,
};
