import { VStack } from "@chakra-ui/react";

import type { MatrixSituationCardProps } from "./MatrixSituationCard";
import MatrixSituationCard from "./MatrixSituationCard";

export interface MatrixSituationCardsProps extends Omit<
  MatrixSituationCardProps,
  "situation"
> {
  situations: MatrixSituationCardProps["situation"][];
}

/** Phone-width transpose of the grid: one card per situation. */
export default function MatrixSituationCards({
  situations,
  ...rest
}: MatrixSituationCardsProps) {
  return (
    <VStack align="stretch" gap={3}>
      {situations.map((situation) => (
        <MatrixSituationCard
          key={situation.code}
          situation={situation}
          {...rest}
        />
      ))}
    </VStack>
  );
}
