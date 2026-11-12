import { Text } from "@chakra-ui/react";

import type { DocumentTextBlock } from "../../../../types/documentTranslation";
import { langOf } from "./blockGroups";

export interface DocumentTextProps {
  block: DocumentTextBlock;
}

/** A paragraph of the page. */
export default function DocumentText({ block }: DocumentTextProps) {
  return (
    <Text lang={langOf(block)} overflowWrap="anywhere" hyphens="auto">
      {block.text}
    </Text>
  );
}
