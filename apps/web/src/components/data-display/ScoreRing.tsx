import { ProgressCircle } from "@chakra-ui/react";

export interface ScoreRingProps {
  /** Whole percent in 0..100; callers clamp. */
  value: number;
  /** Accessible name and tooltip of the ring. */
  label: string;
  /** Colour of the whole ring; the value sector is its darker shade. */
  palette: "red" | "yellow" | "green";
}

/** A ring showing a percentage in a palette colour: the whole ring tinted, the value as the darker sector. */
export default function ScoreRing({ value, label, palette }: ScoreRingProps) {
  return (
    <ProgressCircle.Root
      value={value}
      size="sm"
      colorPalette={palette}
      title={label}
    >
      <ProgressCircle.Circle aria-label={label}>
        <ProgressCircle.Track />
        <ProgressCircle.Range />
      </ProgressCircle.Circle>
      <ProgressCircle.ValueText />
    </ProgressCircle.Root>
  );
}
