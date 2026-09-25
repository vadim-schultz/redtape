import { Box, Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import type { RequirementRead } from "../../../types";

export interface RequirementItemProps {
  requirement: RequirementRead;
}

export default function RequirementItem({ requirement }: RequirementItemProps) {
  return (
    <Box>
      <Link
        asChild
        color="text.link"
        fontWeight="semibold"
        _hover={{ textDecoration: "underline" }}
      >
        <RouterLink to={`/documents/${requirement.required_document.id}`}>
          {requirement.required_document.title}
        </RouterLink>
      </Link>

      {requirement.notes ? (
        <Box as="p" mt={1} color="text.secondary">
          {requirement.notes}
        </Box>
      ) : null}
    </Box>
  );
}
