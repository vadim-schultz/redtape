import { Heading, VStack } from "@chakra-ui/react";
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
      <CandidateSources sources={sources} />
    </VStack>
  );
}
