import { Wrap } from "@chakra-ui/react";

import CategoryChip from "../../../../components/data-display/CategoryChip";
import type { DocumentTag } from "../../types";
import { buildDocumentsHref } from "../../utils/buildDocumentsHref";

export interface DocumentTagBadgesProps {
  tags: DocumentTag[];
}

/** The canonical category links of a card in confidence order. */
export default function DocumentTagBadges({ tags }: DocumentTagBadgesProps) {
  if (tags.length === 0) return null;

  return (
    <Wrap gap={1} mt={2}>
      {tags.map((category) => (
        <CategoryChip
          key={category.code}
          category={category}
          to={buildDocumentsHref({ category: category.code })}
        />
      ))}
    </Wrap>
  );
}
