import { Button, Heading, Text, VStack } from "@chakra-ui/react";
import type { UseQueryResult } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import type { TranslationText } from "../../../services/candidateTranslationApi";
import LoadingNote from "../../feedback/LoadingNote";

export interface TranslationBodyProps {
  query: UseQueryResult<TranslationText>;
}

function Failed({ onRetry }: { onRetry: () => void }) {
  const { t } = useLocale();

  return (
    <VStack align="start" gap={2}>
      <Text role="alert">{t("documents.translation_error")}</Text>
      <Button size="sm" variant="outline" onClick={onRetry}>
        {t("common.retry")}
      </Button>
    </VStack>
  );
}

function Notes({ stale }: { stale: boolean }) {
  const { t } = useLocale();

  return (
    <>
      <Text color="muted" textStyle="caption">
        {t("documents.translation_machine_note")}
      </Text>
      {stale ? (
        <Text color="muted" textStyle="caption">
          {t("documents.translation_stale_note")}
        </Text>
      ) : null}
    </>
  );
}

/** The pop-over content: a loading note, the retry message, or the translated title and description with their notes. */
export default function TranslationBody({ query }: TranslationBodyProps) {
  const { data } = query;

  if (query.isError) return <Failed onRetry={() => void query.refetch()} />;
  if (!data) return <LoadingNote />;

  return (
    <VStack align="stretch" gap={2}>
      <Heading as="h3" textStyle="subsectionHeader" lang={data.locale}>
        {data.title}
      </Heading>
      <Text lang={data.locale} overflowWrap="anywhere" hyphens="auto">
        {data.description}
      </Text>
      <Notes stale={data.stale} />
    </VStack>
  );
}
