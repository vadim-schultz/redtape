import {
  defineListSpec,
  type ListQuerySpec,
} from "../../../services/listQuery";
import { DOCUMENT_SORT_KEYS, type DocumentSortKey } from "../types";

/** Search, sort and page of the documents list; the taxonomy chips are not part of the spec. */
export const DOCUMENT_LIST_SPEC: ListQuerySpec<DocumentSortKey, never> =
  defineListSpec({ sortKeys: DOCUMENT_SORT_KEYS, filters: {} });
