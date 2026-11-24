import { Box, SimpleGrid, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowAllotment } from "../../types";
import FlowAllotmentMeter from "./FlowAllotmentMeter";
import FlowSpendBar from "./FlowSpendBar";

export interface FlowAllotmentStripProps {
  allotments: FlowAllotment[];
}

/** Every allotment with its meter and its spend. Nothing when the response has no allotments. */
export default function FlowAllotmentStrip({
  allotments,
}: FlowAllotmentStripProps) {
  const { t } = useLocale();
  if (allotments.length === 0) return null;

  return (
    <Box role="group" aria-label={t("discovery_admin.flow.strip_label")}>
      <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>
        {allotments.map((allotment) => (
          <Stack key={allotment.resource} gap={2}>
            <FlowAllotmentMeter allotment={allotment} />
            <FlowSpendBar allotment={allotment} />
          </Stack>
        ))}
      </SimpleGrid>
    </Box>
  );
}
