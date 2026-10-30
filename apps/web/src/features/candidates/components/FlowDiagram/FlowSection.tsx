import { Box, Heading, Text, VStack } from "@chakra-ui/react";
import { useId } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import FlowDiagram from "./FlowDiagram";
import type { FlowCandidate } from "./FlowCards";

export interface FlowSectionProps {
  candidate: FlowCandidate;
}

function hasDependencies({ ingress, egress }: FlowCandidate): boolean {
  return ingress.length + egress.length > 0;
}

/**
 * The Flow section. Below `md` the lists above carry the information, so the
 * heading hides together with the diagram and no empty heading is left behind.
 */
export default function FlowSection({ candidate }: FlowSectionProps) {
  const { t } = useLocale();
  const headingId = useId();

  return (
    <Box
      as="section"
      aria-labelledby={headingId}
      display={{ base: "none", md: "block" }}
    >
      <VStack align="stretch" gap={3}>
        <Heading as="h2" id={headingId} textStyle="sectionHeader">
          {t("candidates.flow")}
        </Heading>
        {hasDependencies(candidate) ? (
          <FlowDiagram candidate={candidate} />
        ) : (
          <Text color="muted">{t("candidates.flow_empty")}</Text>
        )}
      </VStack>
    </Box>
  );
}
