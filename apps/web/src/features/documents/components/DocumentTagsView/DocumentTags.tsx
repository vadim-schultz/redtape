import { Wrap } from "@chakra-ui/react";

import CategoryChip from "../../../../components/data-display/CategoryChip";
import type { CategoryTag } from "../../../taxonomy/types";
import { buildDocumentsHref } from "../../utils/buildDocumentsHref";

export interface DocumentTagsProps {
  categories: CategoryTag[];
}

export default function DocumentTags({ categories }: DocumentTagsProps) {
  if (categories.length === 0) return null;

  return (
    <Wrap gap={2}>
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
