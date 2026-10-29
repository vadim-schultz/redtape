import { Badge } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTagSupport } from "../types";

/** The tagged procedures behind a share, for example 3 for 4 procedures when 75 percent carry the code. */
function taggedProcedures({ procedures, share }: DiscoveryTagSupport): number {
  return share > 0 ? Math.round(procedures / share) : procedures;
}

/** One suggested code with its support; accepted codes stand out, the rest are muted. */
export default function TagSupportChip({
  support,
  name,
}: {
  support: DiscoveryTagSupport;
  name: string;
}) {
  const { t } = useLocale();
  const text = t("discovery_admin.document.tags.support", {
    name,
    procedures: support.procedures,
    total: taggedProcedures(support),
  });

  return (
    <Badge
      data-accepted={support.accepted}
      title={
        support.accepted
          ? t("discovery_admin.document.tags.accepted")
          : undefined
      }
      variant={support.accepted ? "solid" : "subtle"}
      colorPalette={support.accepted ? "green" : "gray"}
    >
      {text}
    </Badge>
  );
}
