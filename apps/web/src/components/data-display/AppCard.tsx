import { Card } from "@chakra-ui/react";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";

import { hoverMotion } from "../../theme/transitions";

export interface AppCardProps {
  /** When set, the whole card is a link and lifts on hover. */
  to?: string;
  children: ReactNode;
}

function LinkedCard({ to, children }: Required<AppCardProps>) {
  return (
    <Card.Root
      asChild
      bg="surface.base"
      shadow="card"
      textDecoration="none"
      transitionProperty="box-shadow, transform"
      {...hoverMotion}
      _hover={{ shadow: "elevated", transform: "translateY(-2px)" }}
    >
      <RouterLink to={to}>
        <Card.Body>{children}</Card.Body>
      </RouterLink>
    </Card.Root>
  );
}

function StaticCard({ children }: { children: ReactNode }) {
  return (
    <Card.Root bg="surface.base" shadow="card">
      <Card.Body>{children}</Card.Body>
    </Card.Root>
  );
}

/** The one card look: the document list and the detail page both use it. */
export default function AppCard({ to, children }: AppCardProps) {
  if (to) return <LinkedCard to={to}>{children}</LinkedCard>;
  return <StaticCard>{children}</StaticCard>;
}
