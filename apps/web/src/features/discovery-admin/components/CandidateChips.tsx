import { Badge, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateCounts } from "../types";

export interface CandidateChipsProps {
  candidates: DiscoveryCandidateCounts;
}

/** Document candidate totals, split by lifecycle status, with the mention count. */
export default function CandidateChips({ candidates }: CandidateChipsProps) {
  const { t } = useLocale();
  const chips = [
    { key: "candidates_total", count: candidates.total },
    { key: "candidates_staged", count: candidates.staged },
    { key: "candidates_emitted", count: candidates.emitted },
    { key: "candidate_mentions", count: candidates.mentions },
  ];

  return (
    <>
      {chips.map(({ key, count }) => (
        <WrapItem key={key}>
          <Badge variant="subtle" colorPalette="purple">
            {t(`discovery_admin.coverage.${key}`, { count })}
          </Badge>
        </WrapItem>
      ))}
    </>
  );
}
