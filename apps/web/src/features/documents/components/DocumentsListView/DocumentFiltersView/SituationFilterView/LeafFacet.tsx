import { HStack } from "@chakra-ui/react";

import FilterChip from "../FilterChip";

export interface LeafFacetProps {
  codes: string[];
  selected: string[];
  onToggle: (code: string) => void;
}

/** A more-specific, PVOG-sourced facet under a situation; renders nothing when empty. */
export default function LeafFacet({
  codes,
  selected,
  onToggle,
}: LeafFacetProps) {
  if (codes.length === 0) return null;

  return (
    <HStack wrap="wrap" gap={2}>
      {codes.map((code) => (
        <FilterChip
          key={code}
          label={code}
          pressed={selected.includes(code)}
          onToggle={() => onToggle(code)}
        />
      ))}
    </HStack>
  );
}
