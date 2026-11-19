import { Box, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { FlowCard } from "../../utils/flowModel";
import FlowStageCard from "./FlowStageCard";
import type { FlowSelection } from "./flowSelection";

export interface FlowListProps {
  cards: FlowCard[];
  selection: FlowSelection;
}

/** The stages as one column in topological order, for a narrow screen. Each item is the card the graph shows. */
export default function FlowList({ cards, selection }: FlowListProps) {
  const { t } = useLocale();

  return (
    <Stack
      as="ol"
      gap={3}
      m={0}
      p={0}
      listStyleType="none"
      aria-label={t("discovery_admin.flow.list_label")}
    >
      {cards.map((card) => (
        <Box as="li" key={card.stage.id}>
          <FlowStageCard
            card={card}
            selected={selection.selectedId === card.stage.id}
            onSelect={selection.onSelect}
          />
        </Box>
      ))}
    </Stack>
  );
}
