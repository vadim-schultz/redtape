import {
  useListQueryState,
  type ListQueryController,
} from "../../../hooks/useListQueryState";
import { DOCUMENT_LIST_SPEC } from "../services/documentListQuery";

/** The URL-backed search and page controls of the documents list. */
export type DocumentList = ListQueryController<never, never>;

/** Search and page of the documents list, read from and written to the URL. */
export function useDocumentListState(): DocumentList {
  return useListQueryState(DOCUMENT_LIST_SPEC);
}
