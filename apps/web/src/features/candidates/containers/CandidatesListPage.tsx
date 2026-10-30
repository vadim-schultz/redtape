import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useDomainsQuery } from "../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../../taxonomy/hooks/useLifeSituationsQuery";
import { CandidatesListView } from "../components/CandidatesListView";
import { useCandidateListState } from "../hooks/useCandidateListState";
import { useCandidatesQuery } from "../hooks/useCandidatesQuery";

/** `/candidates`: the public, ranked list of staged candidates. */
export default function CandidatesListPage() {
  const list = useCandidateListState();
  const query = useCandidatesQuery(list.state);
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();

  return (
    <CandidatesListView
      list={list}
      terms={{
        domains: domains.data ?? [],
        situations: situations.data ?? [],
      }}
      result={{ page: query.data, status: toQueryStatus(query) }}
    />
  );
}
