import { Button, HStack } from "@chakra-ui/react";

import type { Term } from "../../../taxonomy/types";

export interface TermChipRowProps {
  terms: Term[];
  /** The selected code, if any; one chip per axis can be active. */
  active: string | undefined;
  onSelect: (code: string) => void;
}

/** Single-select taxonomy chips: the caller decides what a second click on the active chip does. */
export default function TermChipRow({
  terms,
  active,
  onSelect,
}: TermChipRowProps) {
  return (
    <HStack wrap="wrap" gap={2}>
      {terms.map(({ code, name }) => (
        <Button
          key={code}
          size="sm"
          rounded="full"
          colorPalette={code === active ? "primary" : "gray"}
          variant={code === active ? "solid" : "subtle"}
          aria-pressed={code === active}
          onClick={() => onSelect(code)}
        >
          {name}
        </Button>
      ))}
    </HStack>
  );
}
