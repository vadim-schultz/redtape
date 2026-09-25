import { Button } from "@chakra-ui/react";

export interface DocumentBackButtonProps {
  onBack: () => void;
}

export default function DocumentBackButton({
  onBack,
}: DocumentBackButtonProps) {
  return (
    <Button variant="ghost" size="sm" color="text.link" onClick={onBack}>
      ← Back
    </Button>
  );
}
