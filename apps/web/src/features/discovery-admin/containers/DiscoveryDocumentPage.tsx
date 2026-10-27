import { Text } from "@chakra-ui/react";
import { useParams } from "react-router-dom";

import QueryError from "../../../components/feedback/QueryError";
import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import ArtifactsPanel from "../components/ArtifactsPanel";
import DocumentDetail from "../components/DocumentDetail";
import { useDiscoveryCandidateArtifactsQuery } from "../hooks/useDiscoveryCandidateArtifactsQuery";
import { useDiscoveryCandidateQuery } from "../hooks/useDiscoveryCandidateQuery";

/** Candidate drill-down at ``/admin/discovery/documents/:id``. */
export default function DiscoveryDocumentPage() {
  const { id } = useParams();
  const { t } = useLocale();
  const query = useDiscoveryCandidateQuery(id);
  const artifactsQuery = useDiscoveryCandidateArtifactsQuery(id);

  if (query.isError) return <QueryError onRetry={() => void query.refetch()} />;
  if (!query.data) return <Text>{t("common.loading")}</Text>;
  return (
    <DocumentDetail
      data={query.data}
      evidence={
        <ArtifactsPanel
          status={toQueryStatus(artifactsQuery)}
          artifacts={artifactsQuery.data?.items}
        />
      }
    />
  );
}
