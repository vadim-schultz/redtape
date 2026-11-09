import { Text, VStack } from "@chakra-ui/react";

import type { CandidateNeighbour } from "../../types";
import NeighbourCard from "./NeighbourCard";

export interface NeighbourSectionProps {
  items: CandidateNeighbour[];
  emptyText: string;
}

function NeighbourList({
  items,
  emptyText,
}: {
  items: CandidateNeighbour[];
  emptyText: string;
}) {
  if (items.length === 0) return <Text color="muted">{emptyText}</Text>;

  return (
    <VStack as="ul" align="stretch" gap={3} listStyle="none">
      {items.map((item) => (
        <li key={item.id}>
          <NeighbourCard neighbour={item} />
        </li>
      ))}
    </VStack>
  );
}

/** Render one dependency direction inside its parent accordion item. */
export default function NeighbourSection({
  items,
  emptyText,
}: NeighbourSectionProps) {
  return <NeighbourList items={items} emptyText={emptyText} />;
}
