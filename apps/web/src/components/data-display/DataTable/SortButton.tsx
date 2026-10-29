import { Button } from "@chakra-ui/react";
import type { ReactNode } from "react";
import { LuArrowDown, LuArrowUp, LuArrowUpDown } from "react-icons/lu";

import type { SortOrder } from "./types";

const ICONS = { asc: LuArrowUp, desc: LuArrowDown } as const;

export interface SortButtonProps {
  header: ReactNode;
  order: SortOrder | undefined;
  onSort: () => void;
}

/** Keyboard-operable sort toggle; its accessible name is the column header. */
export default function SortButton({ header, order, onSort }: SortButtonProps) {
  const Icon = order ? ICONS[order] : LuArrowUpDown;

  return (
    <Button variant="plain" size="sm" textStyle="tableHeader" onClick={onSort}>
      {header}
      <Icon aria-hidden="true" />
    </Button>
  );
}
