import { Heading, Text, VStack } from "@chakra-ui/react";

import type { TaggedTerm } from "../../../taxonomy/types";
import { DocumentTags } from "../DocumentTagsView";

export interface DocumentHeaderProps {
  title: string;
  description?: string | null;
  domains?: TaggedTerm[];
  lifeSituations?: TaggedTerm[];
}

export default function DocumentHeader({
  title,
  description,
  domains = [],
  lifeSituations = [],
}: DocumentHeaderProps) {
  return (
    <VStack align="stretch" gap={1}>
      <Heading textStyle="pageTitle">{title}</Heading>
      {description && <Text color="text.secondary">{description}</Text>}
      <DocumentTags domains={domains} lifeSituations={lifeSituations} />
    </VStack>
  );
}
