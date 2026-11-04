import { NativeSelect } from "@chakra-ui/react";

import type { FilterOption } from "../../../components/data-display/DataTable";

export interface FilterSelectProps {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (value: string) => void;
}

/** One labelled native select of the task queue filters. */
export default function FilterSelect({
  label,
  value,
  options,
  onChange,
}: FilterSelectProps) {
  return (
    <NativeSelect.Root size="sm" width="auto" minW="10rem">
      <NativeSelect.Field
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </NativeSelect.Field>
      <NativeSelect.Indicator />
    </NativeSelect.Root>
  );
}
