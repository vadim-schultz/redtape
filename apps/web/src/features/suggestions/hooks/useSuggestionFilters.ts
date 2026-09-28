import { useSearchParams } from "react-router-dom";

export type SuggestionStatusFilter =
  "pending" | "all" | "approved" | "rejected";

export interface SuggestionFilters {
  status: SuggestionStatusFilter;
  kind: string | null;
  jurisdictionId: string | null;
  setStatus: (status: SuggestionStatusFilter) => void;
}

/** URL search params are the single source of truth for list filters. */
export function useSuggestionFilters(): SuggestionFilters {
  const [params, setParams] = useSearchParams();

  return {
    status:
      (params.get("status") as SuggestionStatusFilter | null) ?? "pending",
    kind: params.get("kind"),
    jurisdictionId: params.get("jurisdiction_id"),
    setStatus: (status) =>
      setParams((prev) => {
        const next = new URLSearchParams(prev);
        if (status === "pending") next.delete("status");
        else next.set("status", status);
        return next;
      }),
  };
}
