import { Heading, Stack, Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CataloguePipelineResponse } from "../types";
import { localizedTitle } from "../utils/localizedTitle";
import PipelineTimeline from "./PipelineTimeline";

/** Pipeline drill-down body: title, timeline, counts, and preview and artifacts slots. */
export default function PipelineDetail({
  data,
  preview,
  artifacts,
}: {
  data: CataloguePipelineResponse;
  preview: ReactNode;
  artifacts: ReactNode;
}) {
  const { locale, t } = useLocale();
  const { service, derived_stage, tasks, events } = data;

  return (
    <Stack gap={4} align="stretch">
      <Heading size="md">{localizedTitle(service.title_i18n, locale)}</Heading>
      <PipelineTimeline derivedStage={derived_stage} />
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.pipeline.tasks_count", { count: tasks.length })}
      </Text>
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.pipeline.events_count", { count: events.length })}
      </Text>
      {artifacts}
      {preview}
    </Stack>
  );
}
