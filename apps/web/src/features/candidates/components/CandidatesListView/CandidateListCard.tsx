import { Box, Card, Text } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateCard } from "../../types";
import { CompletenessChips } from "../CompletenessChips";
import { CandidateTagBadges } from "../CandidateTagBadges";

/** Tells the item page the visitor came from the list, so Back can restore its URL state. */
const FROM_LIST = { fromList: true } as const;

export interface CandidateListCardProps {
  candidate: CandidateCard;
}

/** One ranked candidate: title, description, tags and the completeness chips, linking to its item page. */
export default function CandidateListCard({
  candidate,
}: CandidateListCardProps) {
  const { t } = useLocale();

  return (
    <AppCard to={`/candidates/${candidate.id}`} state={FROM_LIST}>
      <Card.Title textStyle="subsectionHeader">{candidate.title}</Card.Title>
      {candidate.description ? (
        <Card.Description mt={1} lineClamp={2}>
          {candidate.description}
        </Card.Description>
      ) : null}
      {candidate.description_source ? (
        <Text color="muted" textStyle="caption">
          {t("candidates.from_source", {
            source: candidate.description_source,
          })}
        </Text>
      ) : null}
      <CandidateTagBadges
        domains={candidate.domains}
        situations={candidate.situations}
      />
      <Box mt={3}>
        <CompletenessChips flags={candidate.flags} />
      </Box>
    </AppCard>
  );
}
