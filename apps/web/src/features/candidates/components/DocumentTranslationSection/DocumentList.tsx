import { List } from "@chakra-ui/react";

import type { DocumentTextBlock } from "../../../../types/documentTranslation";
import DocumentListItem from "./DocumentListItem";

export interface DocumentListProps {
  items: DocumentTextBlock[];
}

/** Consecutive list items of the page, in one list. */
export default function DocumentList({ items }: DocumentListProps) {
  return (
    <List.Root as="ul" ps={5} gap={1}>
      {items.map((item, index) => (
        <DocumentListItem key={index} block={item} />
      ))}
    </List.Root>
  );
}
