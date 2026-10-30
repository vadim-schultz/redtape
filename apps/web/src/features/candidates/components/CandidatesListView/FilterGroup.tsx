import { Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

export interface FilterGroupProps {
  heading: string;
  children: ReactNode;
}

/** A labelled group of filter controls. */
export default function FilterGroup({ heading, children }: FilterGroupProps) {
  return (
    <div role="group" aria-label={heading}>
      <Text textStyle="subsectionHeader" mb={2}>
        {heading}
      </Text>
      {children}
    </div>
  );
}
