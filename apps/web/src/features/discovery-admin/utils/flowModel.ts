import {
  layoutGraph,
  type GraphLayout,
} from "../../../components/data-display/FlowGraph";
import type {
  DiscoveryFlowResponse,
  FlowAllotment,
  FlowResource,
  FlowStage,
} from "../types";

/** One stage with the free allotment it draws on, if it draws on one. */
export interface FlowCard {
  stage: FlowStage;
  allotment: FlowAllotment | null;
}

/**
 * The main allotment of each stage. It mirrors the `allotment` column of the API's `flow/topology.py`, because the
 * response does not carry it. A stage missing here has no allotment.
 */
export const STAGE_ALLOTMENT: Readonly<Partial<Record<string, FlowResource>>> =
  {
    seed: "r2_class_a",
    render: "browser_seconds",
    llm: "neurons",
    capture: "browser_seconds",
    embed: "neurons",
    card_translation: "azure_translator_chars",
    page_translation: "azure_translator_chars",
  };

/** The allotment a stage draws on, found among the response's allotments. */
function allotmentOf(
  stageId: string,
  allotments: readonly FlowAllotment[],
): FlowAllotment | null {
  const resource = STAGE_ALLOTMENT[stageId];
  return (
    allotments.find((allotment) => allotment.resource === resource) ?? null
  );
}

/** One card per stage, in the order the response lists them. */
export function flowCards(flow: DiscoveryFlowResponse): FlowCard[] {
  return flow.stages.map((stage) => ({
    stage,
    allotment: allotmentOf(stage.id, flow.allotments),
  }));
}

/**
 * The positions of the stages and edges, or null when the flow cannot be laid out (a cycle, or an edge to an
 * unknown stage). A null layout is shown as an error rather than crashing the page.
 */
export function flowLayout(flow: DiscoveryFlowResponse): GraphLayout | null {
  try {
    return layoutGraph(
      flow.stages.map(({ id }) => ({ id })),
      flow.edges.map(({ from, to, manual_only }) => ({
        from,
        to,
        dashed: manual_only,
      })),
    );
  } catch {
    return null;
  }
}

/** The cards in the layout's topological order, which is the order the list and the reading order use. */
export function orderedCards(
  cards: readonly FlowCard[],
  layout: GraphLayout,
): FlowCard[] {
  const byId = new Map(cards.map((card) => [card.stage.id, card]));
  return layout.nodes.flatMap(({ id }) => byId.get(id) ?? []);
}
