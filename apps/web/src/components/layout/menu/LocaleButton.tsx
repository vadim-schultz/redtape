import { IconButton } from "@chakra-ui/react";

import type { LocaleRow } from "../../../services/localesApi";
import LocaleLabel from "./LocaleLabel";

interface LocaleButtonProps {
  entry: LocaleRow;
  selected: boolean;
  onSelect: () => void;
}

/** A locale's switch, named by its native name, with the 44 px touch target. */
export default function LocaleButton({
  entry,
  selected,
  onSelect,
}: LocaleButtonProps) {
  return (
    <IconButton
      variant={selected ? "subtle" : "ghost"}
      size="sm"
      minW="11"
      minH="11"
      aria-label={entry.name_native}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <LocaleLabel entry={entry} />
    </IconButton>
  );
}
