import { Badge, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { BudgetRow } from "./budgetRows";
import BudgetMeter from "./BudgetMeter";

export interface TranslatorBudgetMeterProps {
  row: BudgetRow;
}

/** The Azure meter with its period label and, once spent, an exhausted badge. */
export default function TranslatorBudgetMeter({
  row,
}: TranslatorBudgetMeterProps) {
  const { t } = useLocale();

  return (
    <Stack gap={2}>
      <Text fontSize="sm">{row.label}</Text>
      <BudgetMeter
        label={row.label}
        used={row.used}
        cap={row.cap}
        usage={row.usage}
        exhausted={row.exhausted}
      />
      {row.exhausted ? (
        <Badge colorPalette="red" variant="subtle">
          {t("discovery_admin.artifacts.budget_exhausted")}
        </Badge>
      ) : null}
    </Stack>
  );
}
