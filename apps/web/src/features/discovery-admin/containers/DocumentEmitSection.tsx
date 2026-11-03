import { toQueryStatus } from "../../../components/feedback/queryStatus";
import DocumentEmitPanel from "../components/DocumentEmitPanel";
import { useDiscoveryCandidateEmitPreviewQuery } from "../hooks/useDiscoveryCandidateEmitPreviewQuery";

/** The emit state of one candidate: its suggestion when emitted, else the preview of an emit. */
export default function DocumentEmitSection({
  candidateId,
  suggestionId,
}: {
  candidateId: string;
  suggestionId: string | null;
}) {
  const query = useDiscoveryCandidateEmitPreviewQuery(candidateId);

  return (
    <DocumentEmitPanel
      status={toQueryStatus(query)}
      preview={query.data}
      suggestionId={suggestionId}
    />
  );
}
