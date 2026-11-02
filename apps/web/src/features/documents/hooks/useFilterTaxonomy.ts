import { useDomainsQuery } from "../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationGroupsQuery } from "../../taxonomy/hooks/useLifeSituationGroupsQuery";
import { useLifeSituationsQuery } from "../../taxonomy/hooks/useLifeSituationsQuery";
import type { GroupedTerm, Term } from "../../taxonomy/types";

export interface FilterTaxonomy {
  domains: Term[];
  situations: GroupedTerm[];
  groups: Term[];
  isError: boolean;
  onRetry: () => void;
}

/** Taxonomy terms for the filter chips, with one retry for all three queries. */
export function useFilterTaxonomy(): FilterTaxonomy {
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();
  const groups = useLifeSituationGroupsQuery();

  return {
    domains: domains.data ?? [],
    situations: situations.data ?? [],
    groups: groups.data ?? [],
    isError: domains.isError || situations.isError || groups.isError,
    onRetry: () => {
      void domains.refetch();
      void situations.refetch();
      void groups.refetch();
    },
  };
}
