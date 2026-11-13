import { Link, Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentTranslationRead } from "../../../../types/documentTranslation";
import DocumentBlocks from "./DocumentBlocks";
import DocumentStateNote from "./DocumentStateNote";

export interface DocumentReadyProps {
  page: DocumentTranslationRead;
}

/** The translated blocks, with the stale and truncated notes above and the machine note and source link below. */
export default function DocumentReady({ page }: DocumentReadyProps) {
  const { t } = useLocale();

  return (
    <VStack align="stretch" gap={4}>
      {page.stale ? <DocumentStateNote note="stale" /> : null}
      {page.truncated ? <DocumentStateNote note="truncated" /> : null}
      <DocumentBlocks blocks={page.blocks} locale={page.locale} />
      <Text color="muted" textStyle="caption">
        {t("candidates.document_machine_note")}
      </Text>
      {page.source_url ? (
        <Link
          href={page.source_url}
          target="_blank"
          rel="noopener noreferrer"
          alignSelf="flex-start"
        >
          {t("candidates.document_source_link")}
        </Link>
      ) : null}
    </VStack>
  );
}
