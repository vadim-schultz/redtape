import { Wrap } from "@chakra-ui/react";

import CategoryChip from "../../../../components/data-display/CategoryChip";
import { buildDocumentsHref } from "../../../../components/data-display/buildDocumentsHref";
import type { CategoryTag } from "../../types";

export interface CandidateTagBadgesProps {
  categories: CategoryTag[];
}

/** Render canonical category links on a candidate detail header. */
export default function CandidateTagBadges({
  categories,
}: CandidateTagBadgesProps) {
  if (categories.length === 0) return null;

  return (
    <Wrap gap={1} mt={2}>
      {categories.map((category) => (
        <CategoryChip
          key={category.code}
          category={category}
          to={buildDocumentsHref({ category: category.code })}
        />
      ))}
    </Wrap>
  );
}
