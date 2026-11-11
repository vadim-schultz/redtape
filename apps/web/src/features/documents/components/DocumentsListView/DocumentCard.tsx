import { Card, Flex, Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import AppCard from "../../../../components/data-display/AppCard";
import { TranslationPopover } from "../../../../components/data-display/TranslationPopover";
import type { DocumentSummary } from "../../types";
import CardScores from "./CardScores";
import DocumentTagBadges from "./DocumentTagBadges";

export interface DocumentCardProps {
  document: DocumentSummary;
}

/** One listed document: title, description, tags and score rings, linking to its item page. */
export default function DocumentCard({ document }: DocumentCardProps) {
  return (
    <AppCard>
      <Flex align="flex-start" gap={3} wrap="wrap">
        <Card.Title textStyle="subsectionHeader" flex="1 1 12rem">
          <Link asChild>
            <RouterLink
              to={`/candidates/${document.id}`}
              state={{ fromList: true }}
            >
              {document.title}
            </RouterLink>
          </Link>
        </Card.Title>
        <TranslationPopover
          candidateId={document.id}
          summary={document.translation}
          label={document.title}
        />
        <CardScores
          confidence={document.confidence}
          similarity={document.similarity}
        />
      </Flex>
      {document.description ? (
        <Card.Description mt={1}>{document.description}</Card.Description>
      ) : null}
      <DocumentTagBadges tags={document.tags} />
    </AppCard>
  );
}
