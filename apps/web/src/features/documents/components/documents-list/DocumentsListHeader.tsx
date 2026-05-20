import { Heading } from '@chakra-ui/react';

export interface DocumentsListHeaderProps {
  title: string;
}

export default function DocumentsListHeader({ title }: DocumentsListHeaderProps) {
  return <Heading size="lg">{title}</Heading>;
}

