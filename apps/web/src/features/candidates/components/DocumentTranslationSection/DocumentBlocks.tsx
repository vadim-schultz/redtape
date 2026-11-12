import { VStack } from "@chakra-ui/react";
import type { ComponentType } from "react";

import type {
  DocumentBlock,
  DocumentTextBlock,
  DocumentTextKind,
} from "../../../../types/documentTranslation";
import { groupBlocks, type BlockGroup } from "./blockGroups";
import DocumentHeading from "./DocumentHeading";
import DocumentList from "./DocumentList";
import DocumentListItem from "./DocumentListItem";
import DocumentRow from "./DocumentRow";
import DocumentTerm from "./DocumentTerm";
import DocumentText from "./DocumentText";

export interface DocumentBlocksProps {
  blocks: DocumentBlock[];
  /** The page's locale, set on the container; untranslated blocks override it. */
  locale: string;
}

type TextView = ComponentType<{ block: DocumentTextBlock }>;

/** The Chakra view of each text kind. */
const TEXT_VIEWS: Record<DocumentTextKind, TextView> = {
  h1: DocumentHeading,
  h2: DocumentHeading,
  h3: DocumentHeading,
  h4: DocumentHeading,
  h5: DocumentHeading,
  h6: DocumentHeading,
  p: DocumentText,
  li: DocumentListItem,
  dt: DocumentTerm,
};

function BlockView({ block }: { block: DocumentBlock }) {
  if (block.kind === "row") return <DocumentRow block={block} />;
  const View = TEXT_VIEWS[block.kind];
  return <View block={block} />;
}

/** The translated page as Chakra components, in source order. Consecutive list items share one list. */
export default function DocumentBlocks({
  blocks,
  locale,
}: DocumentBlocksProps) {
  return (
    <VStack align="stretch" gap={3} lang={locale}>
      {groupBlocks(blocks).map((group: BlockGroup, index) =>
        group.type === "list" ? (
          <DocumentList key={index} items={group.items} />
        ) : (
          <BlockView key={index} block={group.block} />
        ),
      )}
    </VStack>
  );
}
