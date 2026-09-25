import { HStack, Text } from "@chakra-ui/react";

import type { Term } from "../../../../taxonomy/types";

import FilterChip from "./FilterChip";

export interface FilterGroupProps {
  heading: string;
  terms: Term[];
  selected: string[];
  onToggle: (code: string) => void;
}

export default function FilterGroup({
  heading,
  terms,
  selected,
  onToggle,
}: FilterGroupProps) {
  return (
    <div role="group" aria-label={heading}>
      <Text textStyle="subsectionHeader" mb={2}>
        {heading}
      </Text>
      <HStack wrap="wrap" gap={2}>
        {terms.map((term) => (
          <FilterChip
            key={term.code}
            label={term.name}
            pressed={selected.includes(term.code)}
            onToggle={() => onToggle(term.code)}
          />
        ))}
      </HStack>
    </div>
  );
}
