import { Box, Card } from "@chakra-ui/react";
import type { ReactNode } from "react";

import AppCard from "../../../../components/data-display/AppCard";
import type { CandidateDetail } from "../../types";
import { FLOW_GEOMETRY, type FlowNode } from "../../utils/layoutFlow";
import NeighbourCard from "../CandidateDetailView/NeighbourCard";

export type FlowCandidate = Pick<
  CandidateDetail,
  "title" | "ingress" | "egress"
>;

export interface FlowCardsProps {
  candidate: FlowCandidate;
  nodes: FlowNode[];
}

function CentreCard({ title }: { title: string }) {
  return (
    <Box
      height={`${FLOW_GEOMETRY.cardHeight}px`}
      borderWidth="2px"
      borderColor="accent.solid"
      borderRadius="l3"
      overflow="hidden"
      css={{ "& > div": { height: "100%" } }}
    >
      <AppCard>
        <Card.Title textStyle="subsectionHeader" lineClamp={3}>
          {title}
        </Card.Title>
      </AppCard>
    </Box>
  );
}

function Positioned({
  node,
  children,
}: {
  node: FlowNode;
  children: ReactNode;
}) {
  const { cardWidth, cardHeight } = FLOW_GEOMETRY;
  const style = {
    left: node.x,
    top: node.y,
    width: cardWidth,
    height: cardHeight,
  };

  return (
    <Box position="absolute" style={style} data-flow-node={node.role}>
      {children}
    </Box>
  );
}

function cardFor(candidate: FlowCandidate, node: FlowNode): ReactNode {
  if (node.role === "centre") return <CentreCard title={candidate.title} />;
  return <NeighbourCard neighbour={candidate[node.role][node.index]} />;
}

/** The cards at the positions the layout gives them, in DOM order: ingress, centre, egress. */
export default function FlowCards({ candidate, nodes }: FlowCardsProps) {
  return nodes.map((node) => (
    <Positioned key={`${node.role}-${node.index}`} node={node}>
      {cardFor(candidate, node)}
    </Positioned>
  ));
}
