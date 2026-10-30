import { Badge, HStack, Link, Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateSource } from "../../types";

export interface CandidateSourcesProps {
  sources: CandidateSource[];
}

function SourceTitle({ source }: { source: CandidateSource }) {
  if (!source.portal_url)
    return <Text fontWeight="medium">{source.procedure_title}</Text>;
  return (
    <Link
      href={source.portal_url}
      target="_blank"
      rel="noreferrer"
      fontWeight="medium"
    >
      {source.procedure_title}
    </Link>
  );
}

function SourceItem({ source }: { source: CandidateSource }) {
  const { t } = useLocale();

  return (
    <VStack as="li" align="flex-start" gap={1}>
      <HStack gap={2}>
        <SourceTitle source={source} />
        <Badge size="sm" variant="subtle">
          {t(`candidates.source_role_${source.role}`)}
        </Badge>
      </HStack>
      <Text color="muted" textStyle="caption">
        {source.excerpt}
      </Text>
    </VStack>
  );
}

/** The procedure pages that mention the candidate: link, role chip and the quote. */
export default function CandidateSources({ sources }: CandidateSourcesProps) {
  return (
    <VStack as="ul" align="stretch" gap={3} listStyle="none">
      {sources.map((source, index) => (
        <SourceItem
          key={`${source.procedure_title}:${index}`}
          source={source}
        />
      ))}
    </VStack>
  );
}
