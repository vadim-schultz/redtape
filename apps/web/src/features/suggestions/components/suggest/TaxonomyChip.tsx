import { Button } from "@chakra-ui/react";

export interface TaxonomyChipProps {
  label: string;
  pressed: boolean;
  onToggle: () => void;
}

export default function TaxonomyChip({
  label,
  pressed,
  onToggle,
}: TaxonomyChipProps) {
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
