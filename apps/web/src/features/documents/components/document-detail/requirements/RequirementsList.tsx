import { Box, VStack } from "@chakra-ui/react";

import type { RequirementRead } from "../../../types";

import RequirementItem from "./RequirementItem";

export interface RequirementsListProps {
  requirements: RequirementRead[];
}

export default function RequirementsList({
  requirements,
}: RequirementsListProps) {
  return (
    <Box mt={2}>
      <VStack align="stretch" gap={3}>
        {requirements.map((req) => (
          <RequirementItem key={req.id} requirement={req} />
        ))}
      </VStack>
    </Box>
  );
}
