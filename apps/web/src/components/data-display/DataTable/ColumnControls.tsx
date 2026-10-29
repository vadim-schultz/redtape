import { Button, Input } from "@chakra-ui/react";
import type { ReactNode } from "react";
import { LuArrowDown, LuArrowUp, LuArrowUpDown } from "react-icons/lu";

import type { FilterCapability, SortOrder } from "./types";

const ICONS = { asc: LuArrowUp, desc: LuArrowDown } as const;

export interface SortButtonProps {
  header: ReactNode;
  order: SortOrder | undefined;
  onSort: () => void;
}

/** Keyboard-operable sort toggle; its accessible name is the column header. */
export function SortButton({ header, order, onSort }: SortButtonProps) {
  const Icon = order ? ICONS[order] : LuArrowUpDown;

  return (
    <Button variant="plain" size="sm" textStyle="tableHeader" onClick={onSort}>
      {header}
      <Icon aria-hidden="true" />
    </Button>
  );
}

export interface ColumnFilterProps<FilterKey extends string> {
  filter: FilterCapability<FilterKey>;
  onChange: (value: string) => void;
}

/** Text filter for a column that declared a filter capability. */
export function ColumnFilter<FilterKey extends string>({
  filter,
  onChange,
}: ColumnFilterProps<FilterKey>) {
  return (
    <Input
      size="xs"
      marginTop={1}
      aria-label={filter.label}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
