import type { ReactNode } from "react";
import { SimpleGrid, Text } from "@chakra-ui/react";

interface KeyValueRowProps {
  label: string;
  children: ReactNode;
}

/** Two-column label + control row for panel forms. */
export default function KeyValueRow({ label, children }: KeyValueRowProps) {
  return (
    <SimpleGrid
      data-testid="key-value-row"
      templateColumns="1fr 3fr"
      gapX="3"
      gapY="2"
      alignItems="center"
      w="full"
    >
      <Text color="fg.muted" fontSize="sm">
        {label}
      </Text>
      {children}
    </SimpleGrid>
  );
}
