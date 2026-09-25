import { Heading, Text } from "@chakra-ui/react";

export interface DocumentHeaderProps {
  title: string;
  description?: string | null;
}

export default function DocumentHeader({
  title,
  description,
}: DocumentHeaderProps) {
  return (
    <>
      <Heading textStyle="pageTitle">{title}</Heading>
      {description && (
        <Text color="text.secondary" mt={-2}>
          {description}
        </Text>
      )}
    </>
  );
}
