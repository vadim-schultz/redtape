import { Progress, Stack, Text } from "@chakra-ui/react";

import { nearsStorageCap } from "../../utils/nearsStorageCap";

export interface BudgetMeterProps {
  /** Accessible name of the bar; the table row shows it as visible text. */
  label: string;
  used: number;
  cap: number;
  usage: string;
  exhausted?: boolean;
}

function paletteFor({ used, cap, exhausted }: BudgetMeterProps): string {
  if (exhausted) return "red";
  return nearsStorageCap(used, cap) ? "orange" : "blue";
}

/** One read-only meter: the progress bar and the used and remaining text. */
export default function BudgetMeter(props: BudgetMeterProps) {
  const { label, used, cap, usage } = props;

  return (
    <Stack gap={1} minW="12rem">
      <Progress.Root
        value={used}
        max={Math.max(cap, 1)}
        size="sm"
        colorPalette={paletteFor(props)}
      >
        <Progress.Track aria-label={label}>
          <Progress.Range />
        </Progress.Track>
      </Progress.Root>
      <Text fontSize="xs" color="muted">
        {usage}
      </Text>
    </Stack>
  );
}
