import { Card, Flex, Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

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
    <AppCard>
      <Flex justify="space-between" align="flex-start" gap={3}>
        <Card.Title textStyle="subsectionHeader">
          <Link asChild>
            <RouterLink
              to={`/candidates/${document.id}`}
              state={{ fromList: true }}
            >
              {document.title}
            </RouterLink>
          </Link>
        </Card.Title>
        <ConfidenceCircle confidence={document.confidence} />
      </Flex>
      {document.description ? (
        <Card.Description mt={1}>{document.description}</Card.Description>
      ) : null}
      <DocumentTagBadges tags={document.tags} />
    </AppCard>
  );
}
