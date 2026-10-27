import { Badge } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryMentionRole } from "../types";
import { translateOrRaw } from "../utils/translateOrRaw";

/** The role a document plays in a procedure, as a labelled chip. */
export default function MentionRoleChip({
  role,
}: {
  role: DiscoveryMentionRole;
}) {
  const { t } = useLocale();
  const label = translateOrRaw(
    t,
    `discovery_admin.documents.role_${role}`,
    role,
  );

  return (
    <Badge variant="subtle" colorPalette={role === "form" ? "blue" : "gray"}>
      {label}
    </Badge>
  );
}
