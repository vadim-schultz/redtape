import { Grid, Text } from "@chakra-ui/react";

import type { DocumentRowBlock } from "../../../../types/documentTranslation";
import { langOf } from "./blockGroups";

export interface DocumentRowProps {
  block: DocumentRowBlock;
}

/** A table row as a grid with one column per cell, in source order. */
export default function DocumentRow({ block }: DocumentRowProps) {
  const columns = Math.max(block.cells.length, 1);

  return (
    <Grid
      templateColumns={`repeat(${columns}, minmax(0, 1fr))`}
      gap={3}
      lang={langOf(block)}
    >
      {block.cells.map((cell, index) => (
        <Text key={index} overflowWrap="anywhere">
          {cell}
        </Text>
      ))}
    </Grid>
  );
}
