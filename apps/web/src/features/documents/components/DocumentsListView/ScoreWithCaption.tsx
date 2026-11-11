import { Text, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

export interface ScoreWithCaptionProps {
  caption: string;
  children: ReactNode;
}

/** A ring over its short visible caption; the ring carries the accessible name, so the caption is hidden from it. */
export default function ScoreWithCaption({
  caption,
  children,
}: ScoreWithCaptionProps) {
  return (
    <VStack gap={1} minW={16}>
      {children}
      <Text
        as="span"
        aria-hidden="true"
        fontSize="xs"
        color="muted"
        textAlign="center"
      >
        {caption}
      </Text>
    </VStack>
  );
}
