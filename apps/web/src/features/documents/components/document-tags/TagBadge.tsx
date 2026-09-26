import { Badge, Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

export interface TagBadgeProps {
  to: string;
  name: string;
}

export default function TagBadge({ to, name }: TagBadgeProps) {
  return (
    <Badge asChild colorPalette="gray" variant="subtle">
      <Link asChild>
        <RouterLink to={to}>{name}</RouterLink>
      </Link>
    </Badge>
  );
}
