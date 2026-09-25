import { Card } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { hoverMotion } from "../../../../theme/transitions";
import type { DocumentSummary } from "../../types";

export interface DocumentCardProps {
  document: DocumentSummary;
}

export default function DocumentCard({ document }: DocumentCardProps) {
  return (
    <Card.Root
      asChild
      bg="surface.base"
      shadow="card"
      textDecoration="none"
      transitionProperty="box-shadow, transform"
      {...hoverMotion}
      _hover={{ shadow: "elevated", transform: "translateY(-2px)" }}
    >
      <RouterLink to={`/documents/${document.id}`}>
        <Card.Body>
          <Card.Title textStyle="subsectionHeader">{document.title}</Card.Title>
          {document.description ? (
            <Card.Description mt={1}>{document.description}</Card.Description>
          ) : null}
        </Card.Body>
      </RouterLink>
    </Card.Root>
  );
}
