import { Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowAllotment } from "../../types";
import { flowResourceLabel } from "../../utils/flowLabels";
import BudgetMeter from "../coverage/BudgetMeter";

/** One allotment as a meter: its name in words, its use against the cap, and the figures in words. */
export default function FlowAllotmentMeter({
  allotment,
}: {
  allotment: FlowAllotment;
}) {
  const { t } = useLocale();
  const name = flowResourceLabel(allotment.resource, t);
  const used = Math.round(allotment.used);
  const usage = t("discovery_admin.artifacts.budget_usage", {
    used,
    cap: allotment.cap,
    remaining: Math.max(allotment.cap - used, 0),
  });

  return (
    <Stack gap={1}>
      <Text fontSize="xs" fontWeight="medium">
        {name}
      </Text>
      <BudgetMeter
        label={name}
        used={allotment.used}
        cap={allotment.cap}
        usage={usage}
      />
    </Stack>
  );
}
