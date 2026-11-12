import { Text } from "@chakra-ui/react";

import type { DocumentTextBlock } from "../../../../types/documentTranslation";
import { langOf } from "./blockGroups";

export interface DocumentTermProps {
  block: DocumentTextBlock;
}

/** A definition term of the page, in bold. */
export default function DocumentTerm({ block }: DocumentTermProps) {
  return (
    <Text fontWeight="bold" lang={langOf(block)} overflowWrap="anywhere">
      {block.text}
    </Text>
  );
}
