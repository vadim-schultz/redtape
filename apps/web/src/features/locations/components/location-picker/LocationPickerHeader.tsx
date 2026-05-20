import { Button, HStack, Text } from '@chakra-ui/react';

export interface LocationPickerHeaderProps {
  cancelLabel: string;
  localeLabel: string;
  canReset: boolean;
  onReset: () => void;
}

export default function LocationPickerHeader({
  cancelLabel,
  localeLabel,
  canReset,
  onReset,
}: LocationPickerHeaderProps) {
  return (
    <HStack justify="space-between" gap={3}>
      <Button
        size="sm"
        variant="outline"
        onClick={onReset}
        disabled={!canReset}
      >
        {cancelLabel}
      </Button>
      <Text fontSize="sm" color="muted">
        {localeLabel}
      </Text>
    </HStack>
  );
}

