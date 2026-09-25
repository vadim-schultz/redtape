import { Box, Skeleton, Text } from "@chakra-ui/react";
import { LuFileSearch } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import { useLocale } from "../../../../contexts/LocaleContext";

import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";

export interface DocumentsListQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  listTitleLabel: string;
  documents: DocumentSummary[] | undefined;
}

function LoadingSkeleton() {
  return <Skeleton height="24px" />;
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
  listTitleLabel,
}: {
  documents: DocumentSummary[];
  listTitleLabel: string;
}) {
  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {documents.length} {listTitleLabel}
      </Text>
      <Box display="flex" flexDirection="column" gap={3}>
        {documents.map((d) => (
          <DocumentCard key={d.id} document={d} />
        ))}
      </Box>
    </>
  );
}

function renderListContent({
  isLoading,
  isError,
  onRetry,
  listTitleLabel,
  documents,
}: DocumentsListQueryStatusProps) {
  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <QueryError onRetry={onRetry} />;
  if ((documents?.length ?? 0) === 0) return <EmptyDocumentsState />;

  return (
    <PopulatedDocumentsList
      documents={documents ?? []}
      listTitleLabel={listTitleLabel}
    />
  );
}

export default function DocumentsListQueryStatus(
  props: DocumentsListQueryStatusProps,
) {
  return renderListContent(props);
}
