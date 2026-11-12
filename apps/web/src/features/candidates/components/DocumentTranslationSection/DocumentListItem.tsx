import { List } from "@chakra-ui/react";

import type { DocumentTextBlock } from "../../../../types/documentTranslation";
import { langOf } from "./blockGroups";

export interface DocumentListItemProps {
  block: DocumentTextBlock;
}

/** One item of a list of the page. */
export default function DocumentListItem({ block }: DocumentListItemProps) {
  return (
    <List.Item lang={langOf(block)} overflowWrap="anywhere">
      {block.text}
    </List.Item>
  );
}
