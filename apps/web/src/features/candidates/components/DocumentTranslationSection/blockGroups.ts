import {
  DOCUMENT_TEXT_KINDS,
  type DocumentBlock,
  type DocumentTextBlock,
} from "../../../../types/documentTranslation";

/** Consecutive list items share one list; any other block stands alone. */
export type BlockGroup =
  | { type: "list"; items: DocumentTextBlock[] }
  | { type: "block"; block: DocumentBlock };

function isKnownBlock(block: DocumentBlock): boolean {
  return (
    block.kind === "row" ||
    DOCUMENT_TEXT_KINDS.some((kind) => kind === block.kind)
  );
}

function addBlock(groups: BlockGroup[], block: DocumentBlock): BlockGroup[] {
  const last = groups.at(-1);
  if (block.kind === "li" && last?.type === "list") last.items.push(block);
  else if (block.kind === "li") groups.push({ type: "list", items: [block] });
  else groups.push({ type: "block", block });
  return groups;
}

/** The blocks in order, with consecutive list items grouped. A block of an unknown kind is dropped. */
export function groupBlocks(blocks: DocumentBlock[]): BlockGroup[] {
  return blocks.filter(isKnownBlock).reduce<BlockGroup[]>(addBlock, []);
}

/** The `lang` of a block: German for text kept untranslated, none otherwise. */
export function langOf(block: { untranslated: boolean }): string | undefined {
  return block.untranslated ? "de" : undefined;
}
