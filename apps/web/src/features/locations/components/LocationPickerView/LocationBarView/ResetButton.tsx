import { CloseButton } from "@chakra-ui/react";

export interface ResetButtonProps {
  label: string;
  onReset: () => void;
}

export default function ResetButton({ label, onReset }: ResetButtonProps) {
  return (
    <CloseButton
      size="xs"
      borderRadius="full"
      aria-label={label}
      onClick={onReset}
      mx={1}
    />
  );
}
