import { Badge } from "@chakra-ui/react";
import { LuBot, LuUser } from "react-icons/lu";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { SubmitterRead } from "../../types";

const ICON: Record<SubmitterRead["kind"], typeof LuUser> = {
  user: LuUser,
  crawler: LuBot,
};

export interface SourceBadgeProps {
  kind: SubmitterRead["kind"];
}

export default function SourceBadge({ kind }: SourceBadgeProps) {
  const { t } = useLocale();
  const Icon = ICON[kind];
  const labelKey = kind === "crawler" ? "source_crawler" : "source_human";

  return (
    <Badge
      variant="subtle"
      colorPalette="gray"
      display="inline-flex"
      alignItems="center"
      gap={1}
    >
      <Icon aria-hidden />
      {t(`suggestions.${labelKey}`)}
    </Badge>
  );
}
