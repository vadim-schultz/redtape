import { Accordion, Span, VStack } from "@chakra-ui/react";
import { useState, type ReactNode } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateDetail } from "../../types";
import { DocumentTranslationSection } from "../DocumentTranslationSection";
import { FlowSection } from "../FlowDiagram";
import CandidateEvidence from "./CandidateEvidence";
import CandidateHeader from "./CandidateHeader";
import CandidateSources from "./CandidateSources";
import NeighbourSection from "./NeighbourSection";

export interface CandidateDetailContentProps {
  candidate: CandidateDetail;
  screenshotUrl: string;
}

type DetailSection =
  "ingress" | "egress" | "flow" | "evidence" | "sources" | "document";

const DEFAULT_OPEN: DetailSection[] = ["ingress", "egress", "flow"];

/** The German page is the source text, so its translation is not offered in German. */
const GERMAN = "de";

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
      <Accordion.ItemTrigger minH="11">
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
  const { t, locale } = useLocale();
  const [openItems, setOpenItems] = useState<string[]>(DEFAULT_OPEN);

  return (
    <VStack align="stretch" gap={8}>
      <CandidateHeader candidate={candidate} />
      <Accordion.Root
        multiple
        value={openItems}
        onValueChange={(details) => setOpenItems(details.value)}
      >
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
        {locale === GERMAN ? null : (
          <AccordionSection
            value="document"
            title={t("candidates.document_title")}
          >
            <DocumentTranslationSection
              candidateId={candidate.id}
              enabled={openItems.includes("document")}
            />
          </AccordionSection>
        )}
      </Accordion.Root>
    </VStack>
  );
}
