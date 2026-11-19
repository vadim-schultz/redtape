import { type ReactNode } from "react";

import {
  FlowGraph,
  type GraphLayout,
} from "../../../../components/data-display/FlowGraph";
import { useLocale } from "../../../../contexts/LocaleContext";
import { useNarrowScreen } from "../../hooks/useNarrowScreen";
import { orderedCards, type FlowCard } from "../../utils/flowModel";
import FlowList from "./FlowList";
import FlowStageCard from "./FlowStageCard";
import type { FlowSelection } from "./flowSelection";

export interface FlowBoardProps {
  cards: FlowCard[];
  layout: GraphLayout;
  selection: FlowSelection;
}

/** The card of one stage id, selected when it is the chosen stage. */
function cardNode(
  cards: FlowCard[],
  selection: FlowSelection,
): (id: string) => ReactNode {
  const byId = new Map(cards.map((card) => [card.stage.id, card]));
  return (id) => {
    const card = byId.get(id);
    if (!card) return null;
    return (
      <FlowStageCard
        card={card}
        selected={selection.selectedId === id}
        onSelect={selection.onSelect}
      />
    );
  };
}

/** The stages as a graph on a wide screen and as a list below the md breakpoint. Both show the same cards. */
export default function FlowBoard({
  cards,
  layout,
  selection,
}: FlowBoardProps) {
  const { t } = useLocale();
  const narrow = useNarrowScreen();
  if (narrow) {
    return (
      <FlowList cards={orderedCards(cards, layout)} selection={selection} />
    );
  }

  return (
    <FlowGraph
      layout={layout}
      label={t("discovery_admin.flow.graph_label")}
      renderNode={cardNode(cards, selection)}
    />
  );
}
