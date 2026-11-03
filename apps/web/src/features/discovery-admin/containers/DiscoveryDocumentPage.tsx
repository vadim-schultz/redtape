import { Text } from "@chakra-ui/react";
import { useParams } from "react-router-dom";

import NotFoundView from "../../../components/feedback/NotFoundView";
import QueryBoundary from "../../../components/feedback/QueryBoundary";
import {
  loadingUntilData,
  toQueryStatus,
} from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
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
  const { t } = useLocale();
  const query = useDiscoveryCandidateQuery(id);
  usePrefetchDocumentSections(id);

  if (isNotFound(query.error)) return <NotFoundView />;
  const { data } = query;
  const status = loadingUntilData(toQueryStatus(query), data !== undefined);

  return (
    <QueryBoundary status={status} loading={<Text>{t("common.loading")}</Text>}>
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
