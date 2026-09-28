import { Heading } from "@chakra-ui/react";

export interface SuggestionsListHeaderProps {
  title: string;
}

export default function SuggestionsListHeader({
  title,
}: SuggestionsListHeaderProps) {
  return <Heading textStyle="pageTitle">{title}</Heading>;
}
