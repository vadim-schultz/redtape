import { Stack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CompletenessFlags } from "../../types";
import FlagChip from "./FlagChip";

export interface CompletenessChipsProps {
  flags: CompletenessFlags;
  /** `vertical` stacks the chips as a checklist; the default is a wrapping row. */
  orientation?: "horizontal" | "vertical";
}

const FLAG_LABELS = [
  ["has_domain", "candidates.flag_domain"],
  ["has_situation", "candidates.flag_situation"],
  ["has_edges", "candidates.flag_edges"],
  ["has_snapshot", "candidates.flag_snapshot"],
  ["has_screenshot", "candidates.flag_screenshot"],
] as const satisfies readonly (readonly [keyof CompletenessFlags, string])[];

const LAYOUTS = {
  horizontal: { direction: "row" },
  vertical: { direction: "column", align: "flex-start" },
} as const;

/** The five completeness flags as labelled chips; shared by the list and the item page. */
export default function CompletenessChips({
  flags,
  orientation = "horizontal",
}: CompletenessChipsProps) {
  const { t } = useLocale();

  return (
    <Stack
      as="ul"
      listStyle="none"
      {...LAYOUTS[orientation]}
      wrap="wrap"
      gap={1}
    >
      {FLAG_LABELS.map(([flag, labelKey]) => (
        <FlagChip key={flag} label={t(labelKey)} present={flags[flag]} />
      ))}
    </Stack>
  );
}
