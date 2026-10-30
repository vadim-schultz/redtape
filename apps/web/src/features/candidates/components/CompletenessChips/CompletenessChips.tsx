import { HStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CompletenessFlags } from "../../types";
import FlagChip from "./FlagChip";

export interface CompletenessChipsProps {
  flags: CompletenessFlags;
}

const FLAG_LABELS = [
  ["has_domain", "candidates.flag_domain"],
  ["has_situation", "candidates.flag_situation"],
  ["has_edges", "candidates.flag_edges"],
  ["has_snapshot", "candidates.flag_snapshot"],
  ["has_screenshot", "candidates.flag_screenshot"],
] as const satisfies readonly (readonly [keyof CompletenessFlags, string])[];

/** The five completeness flags as labelled chips; shared by the list and the item page. */
export default function CompletenessChips({ flags }: CompletenessChipsProps) {
  const { t } = useLocale();

  return (
    <HStack as="ul" listStyle="none" wrap="wrap" gap={1}>
      {FLAG_LABELS.map(([flag, labelKey]) => (
        <FlagChip key={flag} label={t(labelKey)} present={flags[flag]} />
      ))}
    </HStack>
  );
}
