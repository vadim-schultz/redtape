import { Button } from "@chakra-ui/react";

import { chipLook, type ChipTone } from "./chipLook";

export interface FilterChipProps {
  label: string;
  pressed: boolean;
  onToggle: () => void;
  /** The filter stage the chip belongs to; domains are `plain`. */
  tone?: ChipTone;
  /** A life-area chip that is not selected itself but has situations selected inside. */
  partial?: boolean;
}

export default function FilterChip({
  label,
  pressed,
  onToggle,
  tone = "plain",
  partial = false,
}: FilterChipProps) {
  return (
    <Button
      size="sm"
      rounded="full"
      {...chipLook(tone, pressed, partial)}
      aria-pressed={pressed}
      onClick={onToggle}
    >
      {label}
    </Button>
  );
}
