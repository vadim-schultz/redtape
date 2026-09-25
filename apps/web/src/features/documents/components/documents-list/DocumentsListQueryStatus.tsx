import { Box, Text } from "@chakra-ui/react";
import { LuFileSearch } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import { useLocale } from "../../../../contexts/LocaleContext";

import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";
import DocumentsListSkeleton from "./DocumentsListSkeleton";

export interface DocumentsListQueryStatusProps {
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  documents: DocumentSummary[] | undefined;
}

function EmptyDocumentsState() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuFileSearch}
      title={t("documents.empty_title")}
      description={t("documents.empty_description")}
    />
  );
}

function PopulatedDocumentsList({
  documents,
  isRefreshing,
}: {
  documents: DocumentSummary[];
  isRefreshing: boolean;
}) {
  const { t } = useLocale();
  const countKey = documents.length === 1 ? "count_one" : "count_other";

  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {t(`documents.${countKey}`, { count: documents.length })}
      </Text>
      <Box
        display="flex"
        flexDirection="column"
        gap={3}
        aria-busy={isRefreshing}
        opacity={isRefreshing ? 0.6 : 1}
        transition="opacity 0.2s"
      >
        {documents.map((d) => (
          <DocumentCard key={d.id} document={d} />
        ))}
      </Box>
    </>
  );
}

function renderListContent({
  isLoading,
  isRefreshing,
  isError,
  onRetry,
  documents,
}: DocumentsListQueryStatusProps) {
  if (isLoading) return <DocumentsListSkeleton />;
  if (isError) return <QueryError onRetry={onRetry} />;
  if ((documents?.length ?? 0) === 0) return <EmptyDocumentsState />;

  return (
    <PopulatedDocumentsList
      documents={documents ?? []}
      isRefreshing={isRefreshing}
    />
  );
}

export default function DocumentsListQueryStatus(
  props: DocumentsListQueryStatusProps,
) {
  return renderListContent(props);
}
