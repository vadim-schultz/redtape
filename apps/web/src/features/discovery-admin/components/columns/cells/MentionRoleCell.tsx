import { HStack } from "@chakra-ui/react";

import type { DiscoveryCandidateMention } from "../../../types";
import MentionRoleChip from "../../MentionRoleChip";
import OptionalChip from "../../OptionalChip";

/** A mention's role chip, marked optional when the page says so. */
export default function MentionRoleCell({
  mention,
}: {
  mention: DiscoveryCandidateMention;
}) {
  return (
    <HStack gap={1} wrap="wrap">
      <MentionRoleChip role={mention.role} />
      <OptionalChip isOptional={mention.is_optional} />
    </HStack>
  );
}
