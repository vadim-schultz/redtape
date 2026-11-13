import type { ComponentType } from "react";

import type {
  DocumentBlock,
  DocumentTextBlock,
  DocumentTextKind,
} from "../../../../types/documentTranslation";
import DocumentHeading from "./DocumentHeading";
import DocumentListItem from "./DocumentListItem";
import DocumentRow from "./DocumentRow";
import DocumentTerm from "./DocumentTerm";
import DocumentText from "./DocumentText";

type TextView = ComponentType<{ block: DocumentTextBlock }>;

/** The Chakra view of each text kind; the table covers every kind, so a lookup never misses. */
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

export interface DocumentBlockViewProps {
  block: DocumentBlock;
}

/** One block that is not part of a list: a row, or a text block through its kind's view. */
export default function DocumentBlockView({ block }: DocumentBlockViewProps) {
  if (block.kind === "row") return <DocumentRow block={block} />;
  const View = TEXT_VIEWS[block.kind];
  return <View block={block} />;
}
