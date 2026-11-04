import { Heading, Text, VStack } from "@chakra-ui/react";

import type { CategoryTag } from "../../../taxonomy/types";
import { DocumentTags } from "../DocumentTagsView";

export interface DocumentHeaderProps {
  title: string;
  description?: string | null;
  categories?: CategoryTag[];
}

export default function DocumentHeader({
  title,
  description,
  categories = [],
}: DocumentHeaderProps) {
  return (
    <VStack align="stretch" gap={1}>
      <Heading textStyle="pageTitle">{title}</Heading>
      {description && <Text color="text.secondary">{description}</Text>}
      <DocumentTags categories={categories} />
    </VStack>
  );
}
