import { Wrap } from "@chakra-ui/react";

import type { DiscoveryCandidate } from "../../../types";
import MentionRoleChip from "../../MentionRoleChip";

/** The roles a candidate plays across its mentions, as chips. */
export default function CandidateRolesCell({
  candidate,
}: {
  candidate: DiscoveryCandidate;
}) {
  return (
    <Wrap gap={1}>
      {candidate.roles.map((role) => (
        <MentionRoleChip key={role} role={role} />
      ))}
    </Wrap>
  );
}
