import { Badge, HStack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

const STAGES = ["T0", "T1", "T2", "T3", "T4"] as const;

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
      {STAGES.map((stage) => (
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
