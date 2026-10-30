import { Badge, Box, Card, HStack, Text } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateNeighbour } from "../../types";
import { NEIGHBOUR_CARD_HEIGHT } from "../../utils/neighbourCard";

export interface NeighbourCardProps {
  neighbour: CandidateNeighbour;
}

function EdgeLine({ neighbour }: NeighbourCardProps) {
  const { t } = useLocale();
  const { condition, is_optional } = neighbour;
  if (!condition && !is_optional) return null;

  return (
    <HStack gap={2} mt={1}>
      {condition ? (
        <Text textStyle="caption" color="muted" lineClamp={1}>
          {t("candidates.condition_label", { condition })}
        </Text>
      ) : null}
      {is_optional ? <Badge size="sm">{t("candidates.optional")}</Badge> : null}
    </HStack>
  );
}

/**
 * A compact, fixed-height card for one ingress or egress document. It shares the
 * `AppCard` base with the list card; the text block is not shared yet (two cards).
 */
export default function NeighbourCard({ neighbour }: NeighbourCardProps) {
  return (
    <Box
      height={`${NEIGHBOUR_CARD_HEIGHT}px`}
      css={{ "& > a": { height: "100%" } }}
    >
      <AppCard to={`/candidates/${neighbour.id}`}>
        <Card.Title textStyle="subsectionHeader" lineClamp={1}>
          {neighbour.title}
        </Card.Title>
        <Card.Description lineClamp={1}>
          {neighbour.description ?? neighbour.excerpt}
        </Card.Description>
        <EdgeLine neighbour={neighbour} />
      </AppCard>
    </Box>
  );
}
