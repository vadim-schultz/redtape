import { Box, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowHeadroom } from "../../types";
import { flowResourceLabel, flowStageName } from "../../utils/flowLabels";

export interface FlowHeadroomCalloutProps {
  headroom: FlowHeadroom[];
}

/** One line per resource with unused headroom while a stage that uses it has ready work. Nothing when all is used. */
export default function FlowHeadroomCallout({
  headroom,
}: FlowHeadroomCalloutProps) {
  const { t } = useLocale();
  if (headroom.length === 0) return null;

  return (
    <Stack gap={2}>
      {headroom.map((item) => (
        <Box
          key={`${item.resource}-${item.stage}`}
          role="note"
          backgroundColor="surface"
          borderWidth="1px"
          borderColor="border"
          borderRadius="md"
          px={3}
          py={2}
          fontSize="sm"
        >
          {t("discovery_admin.flow.headroom", {
            resource: flowResourceLabel(item.resource, t),
            stage: flowStageName(item.stage, t),
          })}
        </Box>
      ))}
    </Stack>
  );
}
