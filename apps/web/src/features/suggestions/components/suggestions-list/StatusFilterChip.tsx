import { Button } from "@chakra-ui/react";

export interface StatusFilterChipProps {
  label: string;
  pressed: boolean;
  onSelect: () => void;
}

export default function StatusFilterChip({
  label,
  pressed,
  onSelect,
}: StatusFilterChipProps) {
  return (
    <Button
      size="sm"
      rounded="full"
      colorPalette={pressed ? "primary" : "gray"}
      variant={pressed ? "solid" : "subtle"}
      aria-pressed={pressed}
      onClick={onSelect}
    >
      {label}
    </Button>
  );
}
