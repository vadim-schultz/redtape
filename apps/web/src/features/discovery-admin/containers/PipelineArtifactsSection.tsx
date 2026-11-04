import { toQueryStatus } from "../../../components/feedback/queryStatus";
import ArtifactsPanel from "../components/ArtifactsPanel";
import { useDiscoveryArtifactsQuery } from "../hooks/useDiscoveryArtifactsQuery";

/** The evidence of one catalogue row, loaded for its id. */
export default function PipelineArtifactsSection({
  catalogueId,
}: {
  catalogueId: string;
}) {
  const query = useDiscoveryArtifactsQuery(catalogueId);

  return (
    <ArtifactsPanel
      status={toQueryStatus(query)}
      artifacts={query.data?.items}
    />
  );
}
