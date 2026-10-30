import TruncatedText from "../../../../../components/data-display/TruncatedText";
import type { DiscoveryCandidate } from "../../../types";
import { localizedTitle } from "../../../utils/localizedTitle";
import { candidateHref } from "../candidateRows";

/** Width at which the title column clips its link. */
export const TITLE_MAX_WIDTH = "28rem";

export interface CandidateTitleCellProps {
  candidate: DiscoveryCandidate;
  locale: string;
}

/** The candidate's title as a clipped link to its page; the tooltip shows it whole. */
export default function CandidateTitleCell({
  candidate,
  locale,
}: CandidateTitleCellProps) {
  const title = localizedTitle(candidate.title_i18n, locale) || candidate.key;

  return (
    <TruncatedText maxWidth={TITLE_MAX_WIDTH} to={candidateHref(candidate)}>
      {title}
    </TruncatedText>
  );
}
