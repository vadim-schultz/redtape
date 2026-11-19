import { Badge } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowStageState } from "../../types";
import { FLOW_STATE_META, flowStateLabelKey } from "../../utils/flowStates";

/** A state as an icon and its text label. The colour only reinforces the words. */
export default function FlowStateLabel({ state }: { state: FlowStageState }) {
  const { t } = useLocale();
  const { Icon, palette } = FLOW_STATE_META[state];

  return (
    <Badge
      colorPalette={palette}
      variant="subtle"
      size="sm"
      gap={1}
      alignSelf="flex-start"
    >
      <Icon aria-hidden="true" />
      {t(flowStateLabelKey(state))}
    </Badge>
  );
}
