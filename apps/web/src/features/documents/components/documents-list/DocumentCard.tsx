import { Heading, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

import type { DocumentSummary } from '../../types';

export interface DocumentCardProps {
  document: DocumentSummary;
}

export default function DocumentCard({ document }: DocumentCardProps) {
  return (
    <RouterLink
      to={`/documents/${document.id}`}
      style={{ textDecoration: 'none' }}
    >
      <Heading size="sm">{document.title}</Heading>
      {document.description ? (
        <Text mt={1} color="muted">
          {document.description}
        </Text>
      ) : null}
    </RouterLink>
  );
}

