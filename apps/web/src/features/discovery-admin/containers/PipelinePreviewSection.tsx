import { toQueryStatus } from "../../../components/feedback/queryStatus";
import EmitPreviewPanel from "../components/EmitPreviewPanel";
import { useDiscoveryEmitPreviewQuery } from "../hooks/useDiscoveryEmitPreviewQuery";

/** The emit preview of one catalogue row, loaded for its id. */
export default function PipelinePreviewSection({
  catalogueId,
}: {
  catalogueId: string;
}) {
  const query = useDiscoveryEmitPreviewQuery(catalogueId);

  return (
    <EmitPreviewPanel status={toQueryStatus(query)} items={query.data?.items} />
  );
}
