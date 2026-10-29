import type { UseQueryResult } from "@tanstack/react-query";

import {
  toQueryStatus,
  type QueryStatus,
} from "../../../components/feedback/queryStatus";
import type { CatalogueListQuery } from "../services/catalogueListQuery";
import type {
  CatalogueListResponse,
  DiscoveryCoverageResponse,
} from "../types";
import { useDiscoveryCatalogueQuery } from "./useDiscoveryCatalogueQuery";
import { useDiscoveryCoverageQuery } from "./useDiscoveryCoverageQuery";

type PanelBase = { retry: () => void };

/** State of one independent panel; ``data`` exists only when ready. */
export type PanelState<T> =
  | (PanelBase & { state: "loading" })
  | (PanelBase & { state: "error" })
  | (PanelBase & { state: "ready"; data: T });

/** The catalogue index: its page (kept across a failed refetch) and the query status the table renders. */
export type CataloguePanel = {
  page: CatalogueListResponse | undefined;
  status: QueryStatus;
  pending: boolean;
};

/** Combined catalogue page state; ``ready`` carries per-panel states. */
export type CatalogueState =
  | { kind: "loading" }
  | { kind: "error"; retry: () => void }
  | {
      kind: "ready";
      coverage: PanelState<DiscoveryCoverageResponse>;
      catalogue: CataloguePanel;
    };

function panelState<T>(query: UseQueryResult<T>): PanelState<T> {
  const retry = () => void query.refetch();
  if (query.isPending) return { state: "loading", retry };
  if (query.isError || !query.data) return { state: "error", retry };
  return { state: "ready", data: query.data, retry };
}

function cataloguePanel(
  query: UseQueryResult<CatalogueListResponse>,
): CataloguePanel {
  return {
    page: query.data,
    status: toQueryStatus(query),
    pending: query.isPending,
  };
}

function combine(
  coverage: PanelState<DiscoveryCoverageResponse>,
  catalogue: CataloguePanel,
): CatalogueState {
  const failed = catalogue.status.isError && catalogue.page === undefined;
  if (coverage.state === "loading" && catalogue.pending) {
    return { kind: "loading" };
  }
  if (coverage.state === "error" && failed) {
    return {
      kind: "error",
      retry: () => {
        coverage.retry();
        catalogue.status.onRetry();
      },
    };
  }
  return { kind: "ready", coverage, catalogue };
}

/** Merge the coverage query and the catalogue page of ``query`` into one typed page state. */
export function useCatalogueState(query: CatalogueListQuery): CatalogueState {
  const coverage = panelState(useDiscoveryCoverageQuery());
  const catalogue = cataloguePanel(useDiscoveryCatalogueQuery(query));
  return combine(coverage, catalogue);
}
