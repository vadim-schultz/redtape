import { Box, Flex, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowAllotment } from "../../types";
import { flowRunStageLabel } from "../../utils/flowLabels";

/** Segment colours by position. The legend beside the bar names every segment, so no colour carries a meaning alone. */
const SEGMENT_PALETTES = ["blue", "teal", "purple", "orange", "pink"];

/** A segment's width: its spend as a share of the cap, clamped to the bar. */
function shareOfCap(spent: number, cap: number): string {
  const percent = (spent / Math.max(cap, 1)) * 100;
  return `${Math.min(Math.max(percent, 0), 100)}%`;
}

/** The last day's spend on one allotment: a stacked bar over its cap, and a legend in words beside it. */
export default function FlowSpendBar({
  allotment,
}: {
  allotment: FlowAllotment;
}) {
  const { t } = useLocale();
  const entries = Object.entries(allotment.spent_by_stage);

  return (
    <Stack gap={1}>
      <Flex
        aria-hidden="true"
        height="2"
        borderRadius="full"
        overflow="hidden"
        backgroundColor="bg.muted"
      >
        {entries.map(([stage, spent], index) => (
          <Box
            key={stage}
            height="full"
            width={shareOfCap(spent, allotment.cap)}
            colorPalette={SEGMENT_PALETTES[index % SEGMENT_PALETTES.length]}
            backgroundColor="colorPalette.solid"
          />
        ))}
      </Flex>
      {entries.map(([stage, spent]) => (
        <Text key={stage} fontSize="xs" color="muted">
          {t("discovery_admin.flow.spend_row", {
            stage: flowRunStageLabel(stage, t),
            spent: Math.round(spent),
          })}
        </Text>
      ))}
    </Stack>
  );
}
