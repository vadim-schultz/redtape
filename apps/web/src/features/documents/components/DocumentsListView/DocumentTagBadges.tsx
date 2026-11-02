import { Badge, Wrap } from "@chakra-ui/react";

import type { DocumentTag } from "../../types";

export interface DocumentTagBadgesProps {
  tags: DocumentTag[];
}

/** The tags of a card as plain badges in the order given; the card itself is the link. */
export default function DocumentTagBadges({ tags }: DocumentTagBadgesProps) {
  if (tags.length === 0) return null;

  return (
    <Wrap gap={1} mt={2}>
      {tags.map(({ axis, code, name }) => (
        <Badge key={`${axis}:${code}`} size="sm" variant="subtle">
          {name}
        </Badge>
      ))}
    </Wrap>
  );
}
