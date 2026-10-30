import {
  toQueryStatus,
  type QueryStatus,
} from "../../../components/feedback/queryStatus";
import type { CatalogueListQuery } from "../services/catalogueListQuery";
import type { CatalogueListResponse } from "../types";
import { useDiscoveryCatalogueQuery } from "./useDiscoveryCatalogueQuery";

/** The catalogue index: its page (kept across a failed refetch) and the query status the table renders. */
export type CataloguePanel = {
  page: CatalogueListResponse | undefined;
  status: QueryStatus;
};

/** The catalogue page of ``query``; loading and failure show inside the table so search and filters stay reachable. */
export function useCatalogueState(query: CatalogueListQuery): CataloguePanel {
  const result = useDiscoveryCatalogueQuery(query);
  return { page: result.data, status: toQueryStatus(result) };
}
