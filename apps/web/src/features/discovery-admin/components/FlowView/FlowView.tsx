import { Heading, Stack, Text } from "@chakra-ui/react";
import { useMemo, useState } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { DiscoveryFlowResponse } from "../../types";
import { flowCards, flowLayout } from "../../utils/flowModel";
import FlowAllotmentStrip from "./FlowAllotmentStrip";
import FlowBoard from "./FlowBoard";
import FlowDetailPanel from "./FlowDetailPanel";
import FlowHeadroomCallout from "./FlowHeadroomCallout";
import FlowReadTime from "./FlowReadTime";

export interface FlowViewProps {
  flow: DiscoveryFlowResponse;
  /** When `flow` was read, in milliseconds since the epoch. */
  readAt: number;
}

/** The whole flow: the allotment strip, the unused-headroom callouts, the stages and the detail of the chosen one. */
export default function FlowView({ flow, readAt }: FlowViewProps) {
  const { t } = useLocale();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const cards = useMemo(() => flowCards(flow), [flow]);
  const layout = useMemo(() => flowLayout(flow), [flow]);

  if (flow.stages.length === 0) {
    return <Text>{t("discovery_admin.flow.empty")}</Text>;
  }
  if (!layout) {
    return <Text>{t("discovery_admin.flow.layout_error")}</Text>;
  }

  const selection = { selectedId, onSelect: setSelectedId };
  const selected = cards.find((card) => card.stage.id === selectedId) ?? null;

  return (
    <Stack gap={4}>
      <Heading as="h2" textStyle="sectionHeader">
        {t("discovery_admin.flow.title")}
      </Heading>
      <FlowReadTime readAt={readAt} />
      <FlowAllotmentStrip allotments={flow.allotments} />
      <FlowHeadroomCallout headroom={flow.unused_headroom} />
      <FlowBoard cards={cards} layout={layout} selection={selection} />
      <FlowDetailPanel card={selected} />
    </Stack>
  );
}
