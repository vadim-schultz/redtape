import { Stack, Text } from "@chakra-ui/react";

import SectionCard from "../../../../components/data-display/SectionCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowAllotment } from "../../types";
import { flowStageLabel } from "../../utils/flowLabels";
import type { FlowCard } from "../../utils/flowModel";
import { flowStateDescriptionKey } from "../../utils/flowStates";
import FlowAllotmentMeter from "./FlowAllotmentMeter";
import FlowSpendBar from "./FlowSpendBar";
import FlowStateLabel from "./FlowStateLabel";
import { RunAge, StopReason } from "./FlowRunLines";

export interface FlowDetailPanelProps {
  card: FlowCard | null;
}

/** The spend of the stage's allotment in the last day, or a note that the stage draws on none. */
function SpendSection({ allotment }: { allotment: FlowAllotment | null }) {
  const { t } = useLocale();
  if (!allotment) {
    return (
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.flow.spend_none")}
      </Text>
    );
  }
  return (
    <Stack gap={2}>
      <Text fontSize="sm" fontWeight="medium">
        {t("discovery_admin.flow.spend_title")}
      </Text>
      <FlowAllotmentMeter allotment={allotment} />
      <FlowSpendBar allotment={allotment} />
    </Stack>
  );
}

/** The selected stage in full: its state, its queue numbers, its last run and its spend. */
export default function FlowDetailPanel({ card }: FlowDetailPanelProps) {
  const { t } = useLocale();
  if (!card) {
    return <Text color="muted">{t("discovery_admin.flow.detail_empty")}</Text>;
  }
  const { stage, allotment } = card;

  return (
    <SectionCard title={flowStageLabel(stage, t)}>
      <Stack gap={3}>
        <FlowStateLabel state={stage.state} />
        <Text fontSize="sm">{t(flowStateDescriptionKey(stage.state))}</Text>
        <Text fontSize="sm">
          {t("discovery_admin.flow.ready", { count: stage.ready })}
        </Text>
        <Text fontSize="sm">
          {t("discovery_admin.flow.failed_24h", { count: stage.failed_24h })}
        </Text>
        <RunAge run={stage.last_run} />
        <StopReason run={stage.last_run} />
        <SpendSection allotment={allotment} />
      </Stack>
    </SectionCard>
  );
}
