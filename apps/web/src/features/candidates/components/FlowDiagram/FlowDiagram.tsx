import { Box, Flex, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { layoutFlow, type FlowHidden } from "../../utils/layoutFlow";
import FlowCards, { type FlowCandidate } from "./FlowCards";
import FlowPaths from "./FlowPaths";

export interface FlowDiagramProps {
  candidate: FlowCandidate;
}

function MoreNote({ hidden }: { hidden: FlowHidden }) {
  const { t } = useLocale();
  const note = (count: number) =>
    count > 0 ? (
      <Text color="muted">{t("candidates.flow_more", { count })}</Text>
    ) : (
      <span />
    );

  return (
    <Flex justify="space-between" gap={4} mt={2}>
      {note(hidden.ingress)}
      {note(hidden.egress)}
    </Flex>
  );
}

/** Ingress cards, the central card and egress cards joined by arrows, all placed by `layoutFlow`. */
export default function FlowDiagram({ candidate }: FlowDiagramProps) {
  const { t } = useLocale();
  const { ingress, egress } = candidate;
  const layout = layoutFlow(ingress.length, egress.length);
  const label = t("candidates.flow_summary", {
    ingress: ingress.length,
    egress: egress.length,
  });

  return (
    <Box role="group" aria-label={label} maxWidth="100%">
      <Box overflowX="auto">
        <Box
          position="relative"
          style={{ width: layout.width, height: layout.height }}
        >
          <FlowPaths layout={layout} />
          <FlowCards candidate={candidate} nodes={layout.nodes} />
        </Box>
      </Box>
      <MoreNote hidden={layout.hidden} />
    </Box>
  );
}
