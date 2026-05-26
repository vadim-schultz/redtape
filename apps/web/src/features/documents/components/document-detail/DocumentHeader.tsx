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
      <Heading size="lg">{title}</Heading>
      <Text color="muted" mt={-2}>
        {description}
      </Text>
    </>
  );
}
