import { Heading, Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CompletenessFlags } from "../../types";
import { CompletenessChips } from "../CompletenessChips";

export interface CandidateChecklistProps {
  flags: CompletenessFlags;
  completeness: number;
}

/** The five-item completeness checklist with its "n of 5" count in text. */
export default function CandidateChecklist({
  flags,
  completeness,
}: CandidateChecklistProps) {
  const { t } = useLocale();

  return (
    <VStack align="flex-start" gap={2}>
      <Heading as="h2" textStyle="subsectionHeader">
        {t("candidates.checklist_title")}
      </Heading>
      <Text color="muted">
        {t("candidates.checklist_count", { count: completeness })}
      </Text>
      <CompletenessChips flags={flags} orientation="vertical" />
    </VStack>
  );
}
