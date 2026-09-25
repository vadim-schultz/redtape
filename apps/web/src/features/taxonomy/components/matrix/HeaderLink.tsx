import { Link, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { useDocumentCountLabel } from "../../hooks/useDocumentCountLabel";

export interface HeaderLinkProps {
  to: string;
  name: string;
  total: number;
}

/** Shared look of row and column headers: name, total, visible focus ring. */
export default function HeaderLink({ to, name, total }: HeaderLinkProps) {
  const countLabel = useDocumentCountLabel();

  return (
    <Link
      asChild
      display="block"
      rounded="md"
      p={2}
      color="text.link"
      _focusVisible={{ outline: "2px solid", outlineColor: "focus.outline" }}
    >
      <RouterLink to={to} aria-label={`${name}, ${countLabel(total)}`}>
        <Text as="span" fontWeight="semibold">
          {name}
        </Text>{" "}
        <Text as="span" color="muted" fontSize="sm">
          {total}
        </Text>
      </RouterLink>
    </Link>
  );
}
