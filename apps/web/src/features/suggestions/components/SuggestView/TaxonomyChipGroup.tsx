import { HStack, Text } from "@chakra-ui/react";

import type { Term } from "../../../taxonomy/types";

import TaxonomyChip from "./TaxonomyChip";

export interface TaxonomyChipGroupProps {
  heading: string;
  terms: Term[];
  selected: string[];
  onToggle: (code: string) => void;
}

export default function TaxonomyChipGroup({
  heading,
  terms,
  selected,
  onToggle,
}: TaxonomyChipGroupProps) {
  return (
    <div role="group" aria-label={heading}>
      <Text textStyle="subsectionHeader" mb={2}>
        {heading}
      </Text>
      <HStack wrap="wrap" gap={2}>
        {terms.map((term) => (
          <TaxonomyChip
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
