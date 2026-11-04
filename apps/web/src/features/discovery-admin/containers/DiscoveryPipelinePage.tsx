import { Text } from "@chakra-ui/react";
import { useParams } from "react-router-dom";

import LoadingNote from "../../../components/feedback/LoadingNote";
import QueryBoundary from "../../../components/feedback/QueryBoundary";
import { toQueryStatus } from "../../../components/feedback/queryStatus";
import PipelineDetail from "../components/PipelineDetail";
import { useDiscoveryPipelineQuery } from "../hooks/useDiscoveryPipelineQuery";
import PipelineArtifactsSection from "./PipelineArtifactsSection";
import PipelinePreviewSection from "./PipelinePreviewSection";
import { usePrefetchPipelineSections } from "./sectionPrefetch";

/** Pipeline drill-down at ``/admin/discovery/pipeline/:id``. */
export default function DiscoveryPipelinePage() {
  const { id } = useParams();
  const query = useDiscoveryPipelineQuery(id);
  usePrefetchPipelineSections(id);
  const { data } = query;

  return (
    <QueryBoundary
      status={toQueryStatus(query)}
      loading={<LoadingNote />}
    >
      {data ? (
        <PipelineDetail data={data}>
          <PipelineArtifactsSection catalogueId={data.service.id} />
          <PipelinePreviewSection catalogueId={data.service.id} />
        </PipelineDetail>
      ) : (
        <Text>{t("discovery_admin.pipeline.not_found")}</Text>
      )}
    </QueryBoundary>
  );
}
