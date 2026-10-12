import { Heading, Stack, Text } from "@chakra-ui/react";
import { useParams } from "react-router-dom";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import EmitPreviewPanel from "../components/EmitPreviewPanel";
import PipelineTimeline from "../components/PipelineTimeline";
import { useDiscoveryPipelineQuery } from "../hooks/useDiscoveryPipelineQuery";

function titleForService(
  titleI18n: Record<string, string>,
  locale: string,
): string {
  return (
    titleI18n[locale] ??
    titleI18n.en ??
    titleI18n.de ??
    Object.values(titleI18n)[0] ??
    ""
  );
}

/** Pipeline drill-down at ``/admin/discovery/pipeline/:id``. */
export default function DiscoveryPipelinePage() {
  const { id } = useParams();
  const { locale, t } = useLocale();
  const pipelineQuery = useDiscoveryPipelineQuery(id);

  if (pipelineQuery.isLoading) {
    return <Text>{t("common.loading")}</Text>;
  }
  if (pipelineQuery.isError) {
    return <QueryError onRetry={() => void pipelineQuery.refetch()} />;
  }
  if (!pipelineQuery.data) {
    return <Text>{t("discovery_admin.pipeline.not_found")}</Text>;
  }

  const { service, derived_stage, tasks, events } = pipelineQuery.data;

  return (
    <Stack gap={4} align="stretch">
      <Heading size="md">{titleForService(service.title_i18n, locale)}</Heading>
      <PipelineTimeline derivedStage={derived_stage} />
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.pipeline.tasks_count", { count: tasks.length })}
      </Text>
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.pipeline.events_count", { count: events.length })}
      </Text>
      {id ? <EmitPreviewPanel catalogueId={id} /> : null}
    </Stack>
  );
}
