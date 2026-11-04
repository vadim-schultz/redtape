import { toQueryStatus } from "../../../components/feedback/queryStatus";
import ArtifactsPanel from "../components/ArtifactsPanel";
import { useDiscoveryCandidateArtifactsQuery } from "../hooks/useDiscoveryCandidateArtifactsQuery";

/** The evidence behind one candidate, loaded for its id. */
export default function DocumentEvidenceSection({
  candidateId,
}: {
  candidateId: string;
}) {
  const query = useDiscoveryCandidateArtifactsQuery(candidateId);

  return (
    <ArtifactsPanel
      status={toQueryStatus(query)}
      artifacts={query.data?.items}
    />
  );
}
