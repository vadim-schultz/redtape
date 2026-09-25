import { Button } from "@chakra-ui/react";

export interface FilterChipProps {
  label: string;
  pressed: boolean;
  onToggle: () => void;
}

export default function FilterChip({
  label,
  pressed,
  onToggle,
}: FilterChipProps) {
  return (
    <Button
      size="sm"
      rounded="full"
      colorPalette={pressed ? "primary" : "gray"}
      variant={pressed ? "solid" : "subtle"}
      aria-pressed={pressed}
      onClick={onToggle}
    >
      {label}
    </Button>
  );
}
