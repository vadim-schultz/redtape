import { useDomainsQuery } from "../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../../taxonomy/hooks/useLifeSituationsQuery";
import type { Term } from "../../taxonomy/types";

export interface FilterTaxonomy {
  domains: Term[];
  situations: Term[];
  isError: boolean;
  onRetry: () => void;
}

/** Taxonomy terms for the filter chips, with one retry for both queries. */
export function useFilterTaxonomy(): FilterTaxonomy {
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();

  return {
    domains: domains.data ?? [],
    situations: situations.data ?? [],
    isError: domains.isError || situations.isError,
    onRetry: () => {
      void domains.refetch();
      void situations.refetch();
    },
  };
}
