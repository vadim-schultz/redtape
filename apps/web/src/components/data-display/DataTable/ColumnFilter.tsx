import { IconButton, Popover, Portal } from "@chakra-ui/react";
import { useState } from "react";
import { LuListFilter } from "react-icons/lu";

import FilterDraftForm from "./FilterDraftForm";
import type { FilterCapability } from "./types";

export interface ColumnFilterProps<FilterKey extends string> {
  filter: FilterCapability<FilterKey>;
  /** The applied value; the popover edits a draft and reports only on apply. */
  value: string;
  onChange: (value: string) => void;
}

/** Popover filter of a column that declared a filter capability. */
export default function ColumnFilter<FilterKey extends string>({
  filter,
  value,
  onChange,
}: ColumnFilterProps<FilterKey>) {
  const [open, setOpen] = useState(false);
  const apply = (next: string) => {
    setOpen(false);
    onChange(next);
  };

  return (
    <Popover.Root
      open={open}
      onOpenChange={(details) => setOpen(details.open)}
      positioning={{ placement: "bottom-start" }}
      lazyMount
      unmountOnExit
    >
      <Popover.Trigger asChild>
        <IconButton
          aria-label={filter.label}
          size="2xs"
          variant={value ? "subtle" : "ghost"}
        >
          <LuListFilter aria-hidden="true" />
        </IconButton>
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner>
          <Popover.Content
            aria-label={filter.label}
            backgroundColor="surface.overlay"
            borderWidth="1px"
            borderColor="border"
            shadow="dropdown"
          >
            <Popover.Body>
              <FilterDraftForm filter={filter} value={value} onApply={apply} />
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
}
