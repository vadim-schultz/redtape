import NotFoundView from "../../../../components/feedback/NotFoundView";
import QueryError from "../../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { isNotFound } from "../../../../services/apiErrors";
import type { CandidateDetail } from "../../types";
import CandidateDetailContent from "./CandidateDetailContent";
import CandidateDetailSkeleton from "./CandidateDetailSkeleton";

export interface CandidateDetailQueryStatusProps {
  status: QueryStatus;
  candidate: CandidateDetail | undefined;
  screenshotUrl: string;
}

/** Skeleton while loading, not-found for a 404, a retryable error otherwise, then the content. */
export default function CandidateDetailQueryStatus({
  status,
  candidate,
  screenshotUrl,
}: CandidateDetailQueryStatusProps) {
  if (status.isLoading) return <CandidateDetailSkeleton />;
  if (status.isError && !isNotFound(status.error))
    return <QueryError onRetry={status.onRetry} />;
  if (!candidate) return <NotFoundView />;

  return (
    <CandidateDetailContent
      candidate={candidate}
      screenshotUrl={screenshotUrl}
    />
  );
}
