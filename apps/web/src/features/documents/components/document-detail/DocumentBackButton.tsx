import { Text } from "@chakra-ui/react";

export interface DocumentBackButtonProps {
  onBack: () => void;
}

export default function DocumentBackButton({
  onBack,
}: DocumentBackButtonProps) {
  return (
    <Text as="button" onClick={onBack} color="blue.600" fontSize="sm">
      ←
    </Text>
  );
}
