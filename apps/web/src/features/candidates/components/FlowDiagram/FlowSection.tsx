import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import FlowDiagram from "./FlowDiagram";
import type { FlowCandidate } from "./FlowCards";

export interface FlowSectionProps {
  candidate: FlowCandidate;
}

function hasDependencies({ ingress, egress }: FlowCandidate): boolean {
  return ingress.length + egress.length > 0;
}

/** Render the flow body; its parent accordion owns the heading and responsive visibility. */
export default function FlowSection({ candidate }: FlowSectionProps) {
  const { t } = useLocale();

  return hasDependencies(candidate) ? (
    <FlowDiagram candidate={candidate} />
  ) : (
    <Text color="muted">{t("candidates.flow_empty")}</Text>
  );
}
