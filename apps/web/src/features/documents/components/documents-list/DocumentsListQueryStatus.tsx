import { Box, Skeleton, Text } from '@chakra-ui/react';

import type { DocumentSummary } from '../../types';
import DocumentCard from './DocumentCard';

export interface DocumentsListQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  listTitleLabel: string;
  documents: DocumentSummary[] | undefined;
}

export default function DocumentsListQueryStatus({
  isLoading,
  isError,
  listTitleLabel,
  documents,
}: DocumentsListQueryStatusProps) {
  if (isLoading) {
    return <Skeleton height="24px" />;
  }

  if (isError) {
    return <Text color="muted">Server error</Text>;
  }

  return (
    <>
      <Text mb={2} color="muted" fontSize="sm">
        {(documents?.length ?? 0)} {listTitleLabel}
      </Text>
      <Box display="flex" flexDirection="column" gap={3}>
        {(documents ?? []).map((d) => (
          <DocumentCard key={d.id} document={d} />
        ))}
      </Box>
    </>
  );
}

