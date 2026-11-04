import { Badge, HStack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { PIPELINE_STAGES } from "../types";

export default function PipelineTimeline({
  derivedStage,
}: {
  derivedStage: string;
}) {
  const { t } = useLocale();

  return (
    <HStack gap={2} flexWrap="wrap">
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.pipeline.stage_label")}
      </Text>
      {PIPELINE_STAGES.map((stage) => (
        <Badge
          key={stage}
          colorPalette={stage === derivedStage ? "blue" : "gray"}
          variant={stage === derivedStage ? "solid" : "subtle"}
        >
          {stage}
        </Badge>
      ))}
    </HStack>
  );
}
