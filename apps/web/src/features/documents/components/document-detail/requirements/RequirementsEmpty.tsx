import { Text } from '@chakra-ui/react';

export interface RequirementsEmptyProps {
  label: string;
}

export default function RequirementsEmpty({ label }: RequirementsEmptyProps) {
  return <Text mt={2}>{label}</Text>;
}

