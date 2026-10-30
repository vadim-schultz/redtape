import { Box, Heading, Text, VStack } from "@chakra-ui/react";

import Pagination from "../../../../components/data-display/Pagination";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateList } from "../../hooks/useCandidateListState";
import type { CandidateListResponse } from "../../types";
import { hasActiveFilters } from "../../utils/hasActiveFilters";
import CandidatesBanner from "./CandidatesBanner";
import CandidatesFilters, { type CandidateTerms } from "./CandidatesFilters";
import CandidatesListQueryStatus from "./CandidatesListQueryStatus";

export interface CandidatesListViewProps {
  list: CandidateList;
  terms: CandidateTerms;
  result: { page: CandidateListResponse | undefined; status: QueryStatus };
}

/** The public candidate list: notice, controls, the ranked cards and the pager. */
export default function CandidatesListView({
  list,
  terms,
  result,
}: CandidatesListViewProps) {
  const { t } = useLocale();
  const { offset, limit } = list.state;

  return (
    <VStack align="stretch" gap={6}>
      <Box>
        <Heading textStyle="pageTitle">{t("candidates.title")}</Heading>
        <Text color="muted">{t("candidates.subtitle")}</Text>
      </Box>
      <CandidatesBanner />
      <CandidatesFilters list={list} terms={terms} />
      <CandidatesListQueryStatus
        status={result.status}
        page={result.page}
        onClearFilters={
          hasActiveFilters(list.state) ? list.clearFilters : undefined
        }
      />
      <Pagination
        offset={offset}
        limit={limit}
        total={result.page?.total ?? 0}
        onOffsetChange={list.setOffset}
      />
    </VStack>
  );
}
