import { Accordion, Span, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateDetail } from "../../types";
import { FlowSection } from "../FlowDiagram";
import CandidateEvidence from "./CandidateEvidence";
import CandidateHeader from "./CandidateHeader";
import CandidateSources from "./CandidateSources";
import NeighbourSection from "./NeighbourSection";

export interface CandidateDetailContentProps {
  candidate: CandidateDetail;
  screenshotUrl: string;
}

type DetailSection = "ingress" | "egress" | "flow" | "evidence" | "sources";

const DEFAULT_OPEN: DetailSection[] = ["ingress", "egress", "flow"];

function AccordionSection({
  value,
  title,
  children,
}: {
  value: DetailSection;
  title: string;
  children: ReactNode;
}) {
  return (
    <Accordion.Item value={value}>
      <Accordion.ItemTrigger>
        <Span flex="1">{title}</Span>
        <Accordion.ItemIndicator />
      </Accordion.ItemTrigger>
      <Accordion.ItemContent>{children}</Accordion.ItemContent>
    </Accordion.Item>
  );
}

/** Compose the loaded candidate header and its five accessible detail sections. */
export default function CandidateDetailContent({
  candidate,
  screenshotUrl,
}: CandidateDetailContentProps) {
  const { t } = useLocale();

  return (
    <VStack align="stretch" gap={8}>
      <CandidateHeader candidate={candidate} />
      <Accordion.Root multiple defaultValue={DEFAULT_OPEN}>
        <AccordionSection value="ingress" title={t("candidates.ingress")}>
          <NeighbourSection
            items={candidate.ingress}
            emptyText={t("candidates.ingress_empty")}
          />
        </AccordionSection>
        <AccordionSection value="egress" title={t("candidates.egress")}>
          <NeighbourSection
            items={candidate.egress}
            emptyText={t("candidates.egress_empty")}
          />
        </AccordionSection>
        <AccordionSection value="flow" title={t("candidates.flow")}>
          <FlowSection candidate={candidate} />
        </AccordionSection>
        <AccordionSection value="evidence" title={t("candidates.evidence")}>
          <CandidateEvidence
            candidate={candidate}
            screenshotUrl={screenshotUrl}
          />
        </AccordionSection>
        <AccordionSection value="sources" title={t("candidates.sources")}>
          <CandidateSources sources={candidate.sources} />
        </AccordionSection>
      </Accordion.Root>
    </VStack>
  );
}
