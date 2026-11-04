import { CompletenessChips } from "../../../../../components/data-display/CompletenessChips";
import type { DiscoveryCandidate } from "../../../types";

/** The five completeness flags of a candidate, the same chips the public cards show. */
export default function CandidateReadinessCell({
  candidate,
}: {
  candidate: DiscoveryCandidate;
}) {
  return <CompletenessChips flags={candidate.flags} />;
}
