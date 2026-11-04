import { Badge, Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

export type CategoryChipCategory = {
  code: string;
  name: string;
  confidence: number;
};

export interface CategoryChipProps {
  category: CategoryChipCategory;
  to: string;
}

function opacityFor(confidence: number): number {
  return 0.5 + 0.5 * confidence;
}

/** Render one compact red category link with a visible keyboard focus state. */
export default function CategoryChip({ category, to }: CategoryChipProps) {
  return (
    <Badge
      asChild
      size="sm"
      colorPalette="primary"
      variant="subtle"
      style={{ opacity: opacityFor(category.confidence) }}
    >
      <Link
        asChild
        _focusVisible={{
          outline: "2px solid",
          outlineColor: "focus.ring",
          outlineOffset: "2px",
        }}
      >
        <RouterLink to={to}>{category.name}</RouterLink>
      </Link>
    </Badge>
  );
}
