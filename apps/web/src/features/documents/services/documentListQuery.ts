import {
  defineListSpec,
  type ListQuerySpec,
} from "../../../services/listQuery";

/** Search and page of the documents list; no sort keys, so a stale `sort_by` in the URL is ignored and dropped. */
export const DOCUMENT_LIST_SPEC: ListQuerySpec<never, never> = defineListSpec({
  sortKeys: [],
  filters: {},
});
