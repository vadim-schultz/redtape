import { Card } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import type { DocumentSummary } from "../../types";
import DocumentTagBadges from "./DocumentTagBadges";

export interface DocumentCardProps {
  document: DocumentSummary;
}

/** One listed document: title, description and tags, linking to its item page. */
export default function DocumentCard({ document }: DocumentCardProps) {
  return (
    <AppCard to={`/candidates/${document.id}`}>
      <Card.Title textStyle="subsectionHeader">{document.title}</Card.Title>
      {document.description ? (
        <Card.Description mt={1}>{document.description}</Card.Description>
      ) : null}
      <DocumentTagBadges tags={document.tags} />
    </AppCard>
  );
}
