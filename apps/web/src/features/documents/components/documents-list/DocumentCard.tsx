import { Card } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import type { DocumentSummary } from "../../types";

export interface DocumentCardProps {
  document: DocumentSummary;
}

export default function DocumentCard({ document }: DocumentCardProps) {
  return (
    <AppCard to={`/documents/${document.id}`}>
      <Card.Title textStyle="subsectionHeader">{document.title}</Card.Title>
      {document.description ? (
        <Card.Description mt={1}>{document.description}</Card.Description>
      ) : null}
    </AppCard>
  );
}
