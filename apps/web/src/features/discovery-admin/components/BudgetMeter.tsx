import { Badge, HStack, Progress, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { nearsStorageCap } from "../utils/nearsStorageCap";

export interface BudgetMeterProps {
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

/** One read-only meter: a label, the progress bar and the used and remaining text. */
export default function BudgetMeter(props: BudgetMeterProps) {
  const { t } = useLocale();
  const { label, used, cap, usage, exhausted = false } = props;

  return (
    <Stack gap={1}>
      <HStack gap={2}>
        <Text fontSize="sm">{label}</Text>
        {exhausted ? (
          <Badge colorPalette="red" variant="subtle">
            {t("discovery_admin.artifacts.budget_exhausted")}
          </Badge>
        ) : null}
      </HStack>
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
