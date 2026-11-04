import { useParams } from "react-router-dom";

import LoadingNote from "../../../components/feedback/LoadingNote";
import NotFoundView from "../../../components/feedback/NotFoundView";
import QueryBoundary from "../../../components/feedback/QueryBoundary";
import {
  loadingUntilData,
  toQueryStatus,
} from "../../../components/feedback/queryStatus";
import { isNotFound } from "../../../services/apiErrors";
import DocumentDetail from "../components/DocumentDetail";
import { useDiscoveryCandidateQuery } from "../hooks/useDiscoveryCandidateQuery";
import DocumentEdgesSection from "./DocumentEdgesSection";
import DocumentEmitSection from "./DocumentEmitSection";
import DocumentEvidenceSection from "./DocumentEvidenceSection";
import DocumentTagsSection from "./DocumentTagsSection";
import { usePrefetchDocumentSections } from "./sectionPrefetch";

/** Candidate drill-down at ``/admin/discovery/documents/:id``. */
export default function DiscoveryDocumentPage() {
  const { id } = useParams();
  const query = useDiscoveryCandidateQuery(id);
  usePrefetchDocumentSections(id);

  if (isNotFound(query.error)) return <NotFoundView />;
  const { data } = query;
  const status = loadingUntilData(toQueryStatus(query), data !== undefined);

  return (
    <QueryBoundary status={status} loading={<LoadingNote />}>
      {data ? (
        <DocumentDetail data={data}>
          <DocumentTagsSection data={data} />
          <DocumentEdgesSection candidateId={data.candidate.id} />
          <DocumentEvidenceSection candidateId={data.candidate.id} />
          <DocumentEmitSection
            candidateId={data.candidate.id}
            suggestionId={data.candidate.suggestion_id}
          />
        </DocumentDetail>
      ) : null}
    </QueryBoundary>
  );
}
