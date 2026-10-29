import { useDomainsQuery } from "../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../../taxonomy/hooks/useLifeSituationsQuery";
import type { Term } from "../../taxonomy/types";

function namesByCode(terms: Term[] | undefined): Record<string, string> {
  return Object.fromEntries(
    (Array.isArray(terms) ? terms : []).map(({ code, name }) => [code, name]),
  );
}

/** Display names of the closed domain and life-situation vocabularies, by code; empty while loading. */
export function useTagNames() {
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();

  return {
    domainNames: namesByCode(domains.data),
    situationNames: namesByCode(situations.data),
  };
}
