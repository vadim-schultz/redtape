import { Badge } from "@chakra-ui/react";
import { LuCheck, LuMinus } from "react-icons/lu";

import { useLocale } from "../../../contexts/LocaleContext";

export interface FlagChipProps {
  label: string;
  present: boolean;
}

/** One flag: filled with a check when present, an outline with a dash when missing. */
export default function FlagChip({ label, present }: FlagChipProps) {
  const { t } = useLocale();
  const state = t(
    present ? "candidates.flag_present" : "candidates.flag_missing",
  );
  const Icon = present ? LuCheck : LuMinus;

  return (
    <Badge
      asChild
      size="sm"
      colorPalette={present ? "primary" : "gray"}
      variant={present ? "solid" : "outline"}
    >
      <li aria-label={`${label}: ${state}`}>
        <Icon aria-hidden="true" />
        {label}
      </li>
    </Badge>
  );
}
