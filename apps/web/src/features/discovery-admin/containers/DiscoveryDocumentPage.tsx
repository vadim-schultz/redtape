import { Text } from "@chakra-ui/react";
import { useParams } from "react-router-dom";

import NotFoundView from "../../../components/feedback/NotFoundView";
import QueryError from "../../../components/feedback/QueryError";
import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { ApiRequestError } from "../../../services/api";
import { useLocale } from "../../../contexts/LocaleContext";
import ArtifactsPanel from "../components/ArtifactsPanel";
import DocumentDetail from "../components/DocumentDetail";
import DocumentEdgesPanel from "../components/DocumentEdgesPanel";
import DocumentEmitPanel from "../components/DocumentEmitPanel";
import DocumentTagsPanel from "../components/DocumentTagsPanel";
import { useCandidateEdgesQuery } from "../hooks/useCandidateEdgesQuery";
import { useDiscoveryCandidateArtifactsQuery } from "../hooks/useDiscoveryCandidateArtifactsQuery";
import { useDiscoveryCandidateEmitPreviewQuery } from "../hooks/useDiscoveryCandidateEmitPreviewQuery";
import { useDiscoveryCandidateQuery } from "../hooks/useDiscoveryCandidateQuery";
import { useTagNames } from "../hooks/useTagNames";

function isNotFound(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 404;
}

/** Candidate drill-down at ``/admin/discovery/documents/:id``. */
export default function DiscoveryDocumentPage() {
  const { id } = useParams();
  const { t } = useLocale();
  const query = useDiscoveryCandidateQuery(id);
  const artifactsQuery = useDiscoveryCandidateArtifactsQuery(id);
  const previewQuery = useDiscoveryCandidateEmitPreviewQuery(id);
  const edgesQuery = useCandidateEdgesQuery(id);
  const tagNames = useTagNames();

  if (isNotFound(query.error)) return <NotFoundView />;
  if (query.isError) return <QueryError onRetry={() => void query.refetch()} />;
  if (!query.data) return <Text>{t("common.loading")}</Text>;
  return (
    <DocumentDetail
      data={query.data}
      tags={
        <DocumentTagsPanel
          domains={query.data.suggested_domain_codes}
          situations={query.data.suggested_situation_codes}
          {...tagNames}
        />
      }
      edges={
        <DocumentEdgesPanel
          candidateId={query.data.candidate.id}
          status={toQueryStatus(edgesQuery)}
          edges={edgesQuery.data?.items}
        />
      }
      emit={
        <DocumentEmitPanel
          status={toQueryStatus(previewQuery)}
          preview={previewQuery.data}
          suggestionId={query.data.candidate.suggestion_id}
        />
      }
      evidence={
        <ArtifactsPanel
          status={toQueryStatus(artifactsQuery)}
          artifacts={artifactsQuery.data?.items}
        />
      }
    />
  );
}
