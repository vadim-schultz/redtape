import { Heading, Stack, Text } from "@chakra-ui/react";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import QueryError from "../../../components/feedback/QueryError";
import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import EmitPreviewPanel from "../components/EmitPreviewPanel";
import PipelineTimeline from "../components/PipelineTimeline";
import { useDiscoveryEmitPreviewQuery } from "../hooks/useDiscoveryEmitPreviewQuery";
import { useDiscoveryPipelineQuery } from "../hooks/useDiscoveryPipelineQuery";
import type { CataloguePipelineResponse } from "../types";

type PipelineView =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "missing" }
  | { kind: "ready"; data: CataloguePipelineResponse };

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

function pipelineView(
  query: ReturnType<typeof useDiscoveryPipelineQuery>,
): PipelineView {
  if (query.isLoading) return { kind: "loading" };
  if (query.isError) return { kind: "error" };
  if (!query.data) return { kind: "missing" };
  return { kind: "ready", data: query.data };
}

function PipelineLoading() {
  const { t } = useLocale();
  return <Text>{t("common.loading")}</Text>;
}

function PipelineMissing() {
  const { t } = useLocale();
  return <Text>{t("discovery_admin.pipeline.not_found")}</Text>;
}

function previewPanel(
  id: string | undefined,
  query: ReturnType<typeof useDiscoveryEmitPreviewQuery>,
): ReactNode {
  if (!id) return null;
  return (
    <EmitPreviewPanel status={toQueryStatus(query)} items={query.data?.items} />
  );
}

function PipelineDetail({
  data,
  preview,
}: {
  data: CataloguePipelineResponse;
  preview: ReactNode;
}) {
  const { locale, t } = useLocale();
  const { service, derived_stage, tasks, events } = data;

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
      {preview}
    </Stack>
  );
}

/** Pipeline drill-down at ``/admin/discovery/pipeline/:id``. */
export default function DiscoveryPipelinePage() {
  const { id } = useParams();
  const query = useDiscoveryPipelineQuery(id);
  const previewQuery = useDiscoveryEmitPreviewQuery(id);
  const view = pipelineView(query);

  switch (view.kind) {
    case "loading":
      return <PipelineLoading />;
    case "error":
      return <QueryError onRetry={() => void query.refetch()} />;
    case "missing":
      return <PipelineMissing />;
    case "ready":
      return (
        <PipelineDetail
          data={view.data}
          preview={previewPanel(id, previewQuery)}
        />
      );
  }
}
