import { Box, Heading, Skeleton, Text } from '@chakra-ui/react';

import type { DocumentDetail } from '../../types';

import DocumentHeader from './DocumentHeader';
import DocumentBreadcrumb from './DocumentBreadcrumb';
import RequirementsList from './requirements/RequirementsList';
import RequirementsEmpty from './requirements/RequirementsEmpty';

export interface DocumentDetailQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  document: DocumentDetail | undefined;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

export default function DocumentDetailQueryStatus({
  isLoading,
  isError,
  document,
  requirementsTitle,
  noRequirementsLabel,
  officialSourceTitle,
}: DocumentDetailQueryStatusProps) {
  if (isLoading) {
    return (
      <>
        <Skeleton height="28px" />
        <Skeleton height="18px" />
      </>
    );
  }

  if (isError) {
    return <Text>Server error</Text>;
  }

  if (!document) {
    return null;
  }

  return (
    <>
      <DocumentHeader title={document.title} description={document.description} />
      <DocumentBreadcrumb nodes={document.jurisdiction_path ?? []} />

      <Box mt={4}>
        <Heading size="md">{requirementsTitle}</Heading>
        {document.requirements?.length ? (
          <RequirementsList requirements={document.requirements} />
        ) : (
          <RequirementsEmpty label={noRequirementsLabel} />
        )}
      </Box>

      {document.official_url ? (
        <Box mt={4}>
          <Heading size="sm">{officialSourceTitle}</Heading>
          <Text mt={1}>
            <a href={document.official_url} target="_blank" rel="noreferrer">
              {document.official_url}
            </a>
          </Text>
        </Box>
      ) : null}
    </>
  );
}

