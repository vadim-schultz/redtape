import { Accordion, Heading, Span, VStack } from "@chakra-ui/react";
import { useId } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateDetail } from "../../types";
import CandidateScreenshot from "./CandidateScreenshot";
import CandidateSources from "./CandidateSources";

export interface CandidateEvidenceProps {
  candidate: Pick<CandidateDetail, "title" | "screenshot" | "sources">;
  screenshotUrl: string;
}

/** The screenshot and the sources that back the candidate. */
export default function CandidateEvidence({
  candidate,
  screenshotUrl,
}: CandidateEvidenceProps) {
  const { t } = useLocale();
  const headingId = useId();
  const { title, screenshot, sources } = candidate;

  return (
    <VStack as="section" align="stretch" gap={4} aria-labelledby={headingId}>
      <Heading as="h2" id={headingId} textStyle="sectionHeader">
        {t("candidates.evidence")}
      </Heading>
      <CandidateScreenshot
        src={screenshot ? screenshotUrl : null}
        title={title}
        fetchedAt={screenshot?.fetched_at ?? null}
      />
      <Accordion.Root collapsible defaultValue={[]}>
        <Accordion.Item value="sources">
          <Accordion.ItemTrigger>
            <Span flex="1">{t("candidates.sources")}</Span>
            <Accordion.ItemIndicator />
          </Accordion.ItemTrigger>
          <Accordion.ItemContent>
            <CandidateSources sources={sources} />
          </Accordion.ItemContent>
        </Accordion.Item>
      </Accordion.Root>
    </VStack>
  );
}
