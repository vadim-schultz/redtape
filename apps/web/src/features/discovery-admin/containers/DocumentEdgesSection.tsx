import { toQueryStatus } from "../../../components/feedback/queryStatus";
import DocumentEdgesPanel from "../components/DocumentEdgesPanel";
import { useCandidateEdgesQuery } from "../hooks/useCandidateEdgesQuery";

/** The staged edges of one candidate, loaded for its id. */
export default function DocumentEdgesSection({
  candidateId,
}: {
  candidateId: string;
}) {
  const query = useCandidateEdgesQuery(candidateId);

  return (
    <DocumentEdgesPanel
      candidateId={candidateId}
      status={toQueryStatus(query)}
      edges={query.data?.items}
    />
  );
}
