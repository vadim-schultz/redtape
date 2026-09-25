import { EmptyState } from "@chakra-ui/react";

export interface RequirementsEmptyProps {
  label: string;
}

export default function RequirementsEmpty({ label }: RequirementsEmptyProps) {
  return (
    <EmptyState.Root size="sm">
      <EmptyState.Content>
        <EmptyState.Title>{label}</EmptyState.Title>
      </EmptyState.Content>
    </EmptyState.Root>
  );
}
