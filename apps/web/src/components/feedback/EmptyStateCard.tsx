import { EmptyState, Heading } from "@chakra-ui/react";
import type { ReactNode } from "react";
import type { IconType } from "react-icons";

export interface EmptyStateCardProps {
  icon: IconType;
  title: string;
  description?: string;
  action?: ReactNode;
  variant?: "default" | "error";
  size?: "sm" | "md" | "lg";
}

const iconColor = {
  default: "muted",
  error: "status.error.text",
} as const;

/** One look for every "nothing to show" state: empty, not found, failed. */
export default function EmptyStateCard({
  icon: Icon,
  title,
  description,
  action,
  variant = "default",
  size = "md",
}: EmptyStateCardProps) {
  return (
    <EmptyState.Root role="status" size={size}>
      <EmptyState.Content>
        <EmptyState.Indicator aria-hidden="true" color={iconColor[variant]}>
          <Icon />
        </EmptyState.Indicator>
        <EmptyState.Title asChild>
          <Heading as="h2" textStyle="sectionHeader">
            {title}
          </Heading>
        </EmptyState.Title>
        {description ? (
          <EmptyState.Description>{description}</EmptyState.Description>
        ) : null}
        {action}
      </EmptyState.Content>
    </EmptyState.Root>
  );
}
