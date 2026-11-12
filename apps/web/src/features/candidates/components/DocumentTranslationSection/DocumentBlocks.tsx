import { VStack } from "@chakra-ui/react";

import type { DocumentBlock } from "../../../../types/documentTranslation";
import { groupBlocks } from "./blockGroups";
import DocumentBlockView from "./DocumentBlockView";
import DocumentList from "./DocumentList";

export interface DocumentBlocksProps {
  blocks: DocumentBlock[];
  /** The page's locale, set on the container; untranslated blocks override it. */
  locale: string;
}

/** The translated page as Chakra components, in source order. Consecutive list items share one list. */
export default function DocumentBlocks({
  blocks,
  locale,
}: DocumentBlocksProps) {
  return (
    <VStack align="stretch" gap={3} lang={locale}>
      {groupBlocks(blocks).map((group, index) =>
        group.type === "list" ? (
          <DocumentList key={index} items={group.items} />
        ) : (
          <DocumentBlockView key={index} block={group.block} />
        ),
      )}
    </VStack>
  );
}
