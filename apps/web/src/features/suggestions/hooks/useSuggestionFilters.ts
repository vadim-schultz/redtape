import { useSearchParams } from "react-router-dom";

import { oneOfFilter } from "../../../services/listQuery";
import {
  SUGGESTION_KINDS,
  SUGGESTION_STATUS_FILTERS,
  type SuggestionKind,
  type SuggestionStatusFilter,
} from "../types";

const parseStatus = oneOfFilter(SUGGESTION_STATUS_FILTERS);
const parseKind = oneOfFilter(SUGGESTION_KINDS);

export interface SuggestionFilters {
  status: SuggestionStatusFilter;
  kind: SuggestionKind | null;
  jurisdictionId: string | null;
  setStatus: (status: SuggestionStatusFilter) => void;
}

/** URL search params are the single source of truth for list filters; unknown values fall back. */
export function useSuggestionFilters(): SuggestionFilters {
  const [params, setParams] = useSearchParams();

  return {
    status: parseStatus(params.get("status") ?? "") ?? "pending",
    kind: parseKind(params.get("kind") ?? "") ?? null,
    jurisdictionId: params.get("jurisdiction_id"),
    setStatus: (status) =>
      setParams((prev) => {
        const next = new URLSearchParams(prev);
        if (status === "pending") next.delete("status");
        else next.set("status", status);
        if (parseKind(next.get("kind") ?? "") === undefined) next.delete("kind");
        return next;
      }),
  };
}
