import { Heading, Text, VStack } from "@chakra-ui/react";

export interface DocumentHeaderProps {
  title: string;
  description?: string | null;
}

export default function DocumentHeader({
  title,
  description,
}: DocumentHeaderProps) {
  return (
    <VStack align="stretch" gap={1}>
      <Heading textStyle="pageTitle">{title}</Heading>
      {description && <Text color="text.secondary">{description}</Text>}
    </VStack>
  );
}
