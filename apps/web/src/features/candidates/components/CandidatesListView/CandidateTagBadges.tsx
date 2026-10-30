import { Badge, Wrap } from "@chakra-ui/react";

import type { TaxonomyTag } from "../../types";

export interface CandidateTagBadgesProps {
  domains: TaxonomyTag[];
  situations: TaxonomyTag[];
}

/** The accepted domain and situation tags of a card; plain badges, the card itself is the link. */
export default function CandidateTagBadges({
  domains,
  situations,
}: CandidateTagBadgesProps) {
  const tags = [
    ...domains.map((tag) => ({ ...tag, axis: "domain" })),
    ...situations.map((tag) => ({ ...tag, axis: "situation" })),
  ];
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
