import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentNote } from "./documentState";

/** The translation key of each note. */
const NOTE_KEYS: Record<DocumentNote, string> = {
  pending: "candidates.document_pending",
  no_document: "candidates.document_no_document",
  candidate_not_found: "candidates.document_candidate_not_found",
  skipped: "candidates.document_skipped",
  skipped_too_short: "candidates.document_skipped_too_short",
  skipped_not_german: "candidates.document_skipped_not_german",
  stale: "candidates.document_stale",
  truncated: "candidates.document_truncated",
};

export interface DocumentStateNoteProps {
  note: DocumentNote;
}

/** One caption-sized note about the page: pending, skipped, stale or truncated. */
export default function DocumentStateNote({ note }: DocumentStateNoteProps) {
  const { t } = useLocale();

  return (
    <Text color="muted" textStyle="caption">
      {t(NOTE_KEYS[note])}
    </Text>
  );
}
