import { Card, Stack, Text, chakra } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { flowStageLabel } from "../../utils/flowLabels";
import type { FlowCard } from "../../utils/flowModel";
import FlowAllotmentMeter from "./FlowAllotmentMeter";
import { RunAge, StopReason } from "./FlowRunLines";
import FlowStateLabel from "./FlowStateLabel";

export interface FlowStageCardProps {
  card: FlowCard;
  selected: boolean;
  onSelect: (id: string) => void;
}

/** One stage: its name (the control that selects it), its state, its counts, its last run and its allotment. */
export default function FlowStageCard({
  card,
  selected,
  onSelect,
}: FlowStageCardProps) {
  const { t } = useLocale();
  const { stage, allotment } = card;

  return (
    <Card.Root
      as="article"
      size="sm"
      height="full"
      backgroundColor="surface"
      borderWidth="1px"
      borderColor="border"
      overflow="hidden"
    >
      <Stack gap={1} p={3}>
        <chakra.button
          type="button"
          aria-pressed={selected}
          onClick={() => onSelect(stage.id)}
          textAlign="start"
          fontWeight="semibold"
          fontSize="sm"
          cursor="pointer"
          bg="transparent"
          color="inherit"
          p={0}
        >
          {flowStageLabel(stage, t)}
        </chakra.button>
        <FlowStateLabel state={stage.state} />
        <Text fontSize="xs">
          {t("discovery_admin.flow.ready", { count: stage.ready })}
        </Text>
        <Text fontSize="xs">
          {t("discovery_admin.flow.failed_24h", { count: stage.failed_24h })}
        </Text>
        <RunAge run={stage.last_run} />
        <StopReason run={stage.last_run} />
        {allotment ? <FlowAllotmentMeter allotment={allotment} /> : null}
      </Stack>
    </Card.Root>
  );
}
