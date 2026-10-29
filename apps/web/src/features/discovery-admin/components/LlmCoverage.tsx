import { Badge, Stack, Text, Wrap, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryBudget, DiscoveryLlmOutcomes } from "../types";
import ResourceMeter from "./ResourceMeter";

const OUTCOMES: (keyof DiscoveryLlmOutcomes)[] = [
  "extracted",
  "no_documents",
  "login_wall",
  "no_content",
];

export interface LlmCoverageProps {
  outcomes: DiscoveryLlmOutcomes;
  /** Today's neuron budget; absent while the budgets route has not answered. */
  neurons: DiscoveryBudget | undefined;
}

/** What the model runs produced, per outcome, and the neurons used of today's cap. */
export default function LlmCoverage({ outcomes, neurons }: LlmCoverageProps) {
  const { t } = useLocale();

  return (
    <Stack gap={3} align="stretch" maxW="28rem">
      <Text fontWeight="medium">{t("discovery_admin.coverage.llm.title")}</Text>
      <Wrap gap={2}>
        {OUTCOMES.map((outcome) => (
          <WrapItem key={outcome}>
            <Badge variant="subtle" colorPalette="teal">
              {t(`discovery_admin.coverage.llm.${outcome}`, {
                count: outcomes[outcome],
              })}
            </Badge>
          </WrapItem>
        ))}
      </Wrap>
      {neurons ? <ResourceMeter budget={neurons} /> : null}
    </Stack>
  );
}
