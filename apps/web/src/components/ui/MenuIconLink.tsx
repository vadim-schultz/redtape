import { IconButton } from "@chakra-ui/react";
import type { IconType } from "react-icons";
import { Link as RouterLink } from "react-router-dom";

interface MenuIconLinkProps {
  Icon: IconType;
  label: string;
  to: string;
}

/** Ghost icon button linking to a route, named by a translated label and title. */
export default function MenuIconLink({ Icon, label, to }: MenuIconLinkProps) {
  return (
    <IconButton variant="ghost" size="sm" asChild>
      <RouterLink to={to} aria-label={label} title={label}>
        <Icon aria-hidden="true" />
      </RouterLink>
    </IconButton>
  );
}
