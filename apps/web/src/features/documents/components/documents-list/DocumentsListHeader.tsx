import { Heading } from "@chakra-ui/react";

export interface DocumentsListHeaderProps {
  title: string;
}

export default function DocumentsListHeader({
  title,
}: DocumentsListHeaderProps) {
  return (
    <Heading textStyle="pageTitle" color="text.primary">
      {title}
    </Heading>
  );
}
