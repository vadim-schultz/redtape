/** The kinds of a text block: a heading level, a paragraph, a list item or a definition term. */
export const DOCUMENT_TEXT_KINDS = [
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "p",
  "li",
  "dt",
] as const;

export type DocumentTextKind = (typeof DOCUMENT_TEXT_KINDS)[number];

/** A block of translated text. `untranslated` is true when the German text was kept in its place. */
export type DocumentTextBlock = {
  kind: DocumentTextKind;
  text: string;
  untranslated: boolean;
};

/** A table row: its cells in source order. */
export type DocumentRowBlock = {
  kind: "row";
  cells: string[];
  untranslated: boolean;
};

export type DocumentBlock = DocumentTextBlock | DocumentRowBlock;

/** The codes of the document route's 404 answers: why a page has no blocks to show. */
export const DOCUMENT_TRANSLATION_CODES = [
  "candidate_not_found",
  "no_document",
  "translation_pending",
  "skipped",
] as const;

export type DocumentTranslationCode =
  (typeof DOCUMENT_TRANSLATION_CODES)[number];

/** The translated blocks of a candidate's procedure page in one locale. */
export type DocumentTranslationRead = {
  locale: string;
  source_url: string | null;
  truncated: boolean;
  stale: boolean;
  blocks: DocumentBlock[];
};

/** The 404 body: a code, and the skip reason when the page was skipped. */
export type DocumentTranslationError = {
  code: DocumentTranslationCode;
  reason: string | null;
};
