import { Badge } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { SuggestionStatus } from "../../types";

const PALETTE: Record<SuggestionStatus, string> = {
  pending: "yellow",
  approved: "green",
  rejected: "red",
};

export interface StatusBadgeProps {
  status: SuggestionStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const { t } = useLocale();

  return (
    <Badge colorPalette={PALETTE[status]}>
      {t(`suggestions.status_${status}`)}
    </Badge>
  );
}
