import type { UseQueryResult } from "@tanstack/react-query";

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

/** Combined catalogue page state; ``ready`` carries per-panel states. */
export type CatalogueState =
  | { kind: "loading" }
  | { kind: "error"; retry: () => void }
  | {
      kind: "ready";
      coverage: PanelState<DiscoveryCoverageResponse>;
      catalogue: PanelState<CatalogueListResponse>;
    };

function panelState<T>(query: UseQueryResult<T>): PanelState<T> {
  const retry = () => void query.refetch();
  if (query.isPending) return { state: "loading", retry };
  if (query.isError || !query.data) return { state: "error", retry };
  return { state: "ready", data: query.data, retry };
}

function combine(
  coverage: PanelState<DiscoveryCoverageResponse>,
  catalogue: PanelState<CatalogueListResponse>,
): CatalogueState {
  if (coverage.state === "loading" && catalogue.state === "loading") {
    return { kind: "loading" };
  }
  if (coverage.state === "error" && catalogue.state === "error") {
    return {
      kind: "error",
      retry: () => {
        coverage.retry();
        catalogue.retry();
      },
    };
  }
  return { kind: "ready", coverage, catalogue };
}

/** Merge the coverage and catalogue queries into one typed page state. */
export function useCatalogueState(): CatalogueState {
  const coverage = panelState(useDiscoveryCoverageQuery());
  const catalogue = panelState(useDiscoveryCatalogueQuery());
  return combine(coverage, catalogue);
}
