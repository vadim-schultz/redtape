import { Box, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

import type { RequirementRead } from '../../../types';

export interface RequirementItemProps {
  requirement: RequirementRead;
}

export default function RequirementItem({ requirement }: RequirementItemProps) {
  return (
    <Box>
      <Text fontWeight={600}>
        <RouterLink
          to={`/documents/${requirement.required_document.id}`}
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          {requirement.required_document.title}
        </RouterLink>
      </Text>

      {requirement.notes ? (
        <Text color="muted" mt={1}>
          {requirement.notes}
        </Text>
      ) : null}
    </Box>
  );
}

