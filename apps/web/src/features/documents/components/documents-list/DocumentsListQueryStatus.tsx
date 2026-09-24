import { Alert, Box, EmptyState, Skeleton, Text } from "@chakra-ui/react";

import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";

export interface DocumentsListQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  listTitleLabel: string;
  documents: DocumentSummary[] | undefined;
}

function LoadingSkeleton() {
  return <Skeleton height="24px" />;
}

function ErrorAlert() {
  return (
    <Alert.Root status="error">
      <Alert.Indicator />
      <Alert.Title>Server error</Alert.Title>
    </Alert.Root>
  );
}

function EmptyDocumentsState() {
  return (
    <EmptyState.Root>
      <EmptyState.Content>
        <EmptyState.Title>No documents found</EmptyState.Title>
      </EmptyState.Content>
    </EmptyState.Root>
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
  listTitleLabel,
  documents,
}: DocumentsListQueryStatusProps) {
  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <ErrorAlert />;
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
