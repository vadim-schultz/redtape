import type { DiscoveryCandidateEdge } from "../../../types";
import OptionalChip from "../../OptionalChip";
import LongText from "../LongText";

/** An edge's condition text with the optional marker beside it. */
export default function EdgeConditionCell({
  edge,
}: {
  edge: DiscoveryCandidateEdge;
}) {
  return (
    <LongText>
      {edge.condition} <OptionalChip isOptional={edge.is_optional} />
    </LongText>
  );
}
