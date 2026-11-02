import { Card, Flex } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import type { DocumentSummary } from "../../types";
import { ConfidenceCircle } from "../ConfidenceCircleView";
import DocumentTagBadges from "./DocumentTagBadges";

export interface DocumentCardProps {
  document: DocumentSummary;
}

/** One listed document: title, description, tags and confidence, linking to its item page. */
export default function DocumentCard({ document }: DocumentCardProps) {
  return (
    <AppCard to={`/candidates/${document.id}`} state={{ fromList: true }}>
      <Flex justify="space-between" align="flex-start" gap={3}>
        <Card.Title textStyle="subsectionHeader">{document.title}</Card.Title>
        <ConfidenceCircle confidence={document.confidence} />
      </Flex>
      {document.description ? (
        <Card.Description mt={1}>{document.description}</Card.Description>
      ) : null}
      <DocumentTagBadges tags={document.tags} />
    </AppCard>
  );
}
