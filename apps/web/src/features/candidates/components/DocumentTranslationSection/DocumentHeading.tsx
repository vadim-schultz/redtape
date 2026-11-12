import { Heading } from "@chakra-ui/react";

import type { DocumentTextBlock } from "../../../../types/documentTranslation";
import { langOf } from "./blockGroups";

export interface DocumentHeadingProps {
  block: DocumentTextBlock;
}

/** A heading of the page, at the level of its source (h1 to h6). */
export default function DocumentHeading({ block }: DocumentHeadingProps) {
  return (
    <Heading
      as={block.kind}
      textStyle="subsectionHeader"
      lang={langOf(block)}
      overflowWrap="anywhere"
    >
      {block.text}
    </Heading>
  );
}
