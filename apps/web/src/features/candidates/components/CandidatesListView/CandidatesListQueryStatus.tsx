import QueryStatusView from "../../../../components/feedback/QueryStatusView";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { useCountLabel } from "../../../../components/feedback/useCountLabel";
import type { CandidateListResponse } from "../../types";
import CandidateListCard from "./CandidateListCard";
import CandidatesEmptyState from "./CandidatesEmptyState";
import CandidatesListSkeleton from "./CandidatesListSkeleton";

export interface CandidatesListQueryStatusProps {
  status: QueryStatus;
  page: CandidateListResponse | undefined;
  onClearFilters: (() => void) | undefined;
}

/** Loading, error, empty and populated states of the candidate list; the count is the full result. */
export default function CandidatesListQueryStatus({
  status,
  page,
  onClearFilters,
}: CandidatesListQueryStatusProps) {
  const countLabel = useCountLabel("candidates");

  return (
    <QueryStatusView
      status={status}
      items={page?.items}
      slots={{
        getKey: (candidate) => candidate.id,
        renderItem: (candidate) => <CandidateListCard candidate={candidate} />,
        renderSkeleton: () => <CandidatesListSkeleton />,
        renderEmpty: () => (
          <CandidatesEmptyState onClearFilters={onClearFilters} />
        ),
        countLabel: () => countLabel(page?.total ?? 0),
      }}
    />
  );
}
