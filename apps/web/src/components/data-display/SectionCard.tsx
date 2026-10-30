import { Card, Heading } from "@chakra-ui/react";
import { useId, type ReactNode } from "react";

export interface SectionCardProps {
  /** Heading shown in the shell header; also names the section region. */
  title?: ReactNode;
  /** Controls rendered beside the title, such as filters or actions. */
  toolbar?: ReactNode;
  children: ReactNode;
}

function SectionHeader({
  titleId,
  title,
  toolbar,
}: {
  titleId: string;
  title?: ReactNode;
  toolbar?: ReactNode;
}) {
  if (!title && !toolbar) return null;
  return (
    <Card.Header
      data-section-header=""
      flexDirection="row"
      alignItems="center"
      justifyContent="space-between"
      gap={3}
      borderBottomWidth="1px"
      borderColor="border"
    >
      {title ? (
        <Heading as="h2" id={titleId} textStyle="sectionHeader">
          {title}
        </Heading>
      ) : null}
      {toolbar}
    </Card.Header>
  );
}

/**
 * Raised static shell for admin sections and table containers: semantic
 * surface, subtle border, and the named shell shadow. It never lifts on hover.
 */
export default function SectionCard({
  title,
  toolbar,
  children,
}: SectionCardProps) {
  const titleId = useId();

  return (
    <Card.Root
      as={title ? "section" : "div"}
      aria-labelledby={title ? titleId : undefined}
      data-section-card=""
      backgroundColor="surface"
      borderWidth="1px"
      borderColor="border"
      shadow="shell"
    >
      <SectionHeader titleId={titleId} title={title} toolbar={toolbar} />
      <Card.Body>{children}</Card.Body>
    </Card.Root>
  );
}
