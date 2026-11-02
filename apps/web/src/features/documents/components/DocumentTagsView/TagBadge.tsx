import { Badge, Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

export interface TagBadgeProps {
  to: string;
  name: string;
  confidence: number;
}

/** A continuous confidence gradient, never a binary accepted/rejected style (architecture §2) —
 * `0.5` keeps even a low-confidence tag legible instead of fading it to invisible. */
function opacityFor(confidence: number): number {
  return 0.5 + 0.5 * confidence;
}

export default function TagBadge({ to, name, confidence }: TagBadgeProps) {
  return (
    <Badge
      asChild
      colorPalette="gray"
      variant="subtle"
      style={{ opacity: opacityFor(confidence) }}
    >
      <Link asChild>
        <RouterLink to={to}>{name}</RouterLink>
      </Link>
    </Badge>
  );
}
