import { Text } from "@chakra-ui/react";

import type { JurisdictionPathNode } from "../../types";

export interface DocumentBreadcrumbProps {
  nodes: JurisdictionPathNode[];
  separator?: string;
}

export default function DocumentBreadcrumb({
  nodes,
  separator = " › ",
}: DocumentBreadcrumbProps) {
  if (!nodes.length) {
    return null;
  }

  const label = nodes.map((n) => n.name).join(separator);

  return (
    <Text mt={2} fontSize="sm" color="muted">
      {label}
    </Text>
  );
}
