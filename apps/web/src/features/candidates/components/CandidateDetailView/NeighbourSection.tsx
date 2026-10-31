import { Heading, Text, VStack } from "@chakra-ui/react";
import { useId } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateNeighbour } from "../../types";
import NeighbourCard from "./NeighbourCard";

export type NeighbourKind = "ingress" | "egress";

export interface NeighbourSectionProps {
  kind: NeighbourKind;
  items: CandidateNeighbour[];
}

/** Plain-language heading and empty text of each direction (D2). */
const KEYS = {
  ingress: {
    title: "candidates.ingress",
    empty: "candidates.ingress_empty",
  },
  egress: {
    title: "candidates.egress",
    empty: "candidates.egress_empty",
  },
} as const;

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

/** One direction of the dependency graph as a list of linked neighbour cards. */
export default function NeighbourSection({
  kind,
  items,
}: NeighbourSectionProps) {
  const { t } = useLocale();
  const headingId = useId();
  const keys = KEYS[kind];

  return (
    <VStack as="section" align="stretch" gap={3} aria-labelledby={headingId}>
      <Heading as="h2" id={headingId} textStyle="sectionHeader">
        {t(keys.title)}
      </Heading>
      <NeighbourList items={items} emptyText={t(keys.empty)} />
    </VStack>
  );
}
