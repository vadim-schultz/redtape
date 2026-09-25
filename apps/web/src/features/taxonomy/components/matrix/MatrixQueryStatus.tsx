import QueryError from "../../../../components/feedback/QueryError";
import type { MatrixResponse, Term } from "../../types";
import MatrixEmpty from "./MatrixEmpty";
import MatrixSkeleton from "./MatrixSkeleton";
import MatrixView from "./MatrixView";

export interface MatrixQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  matrix: MatrixResponse | undefined;
  domains: Term[] | undefined;
  situations: Term[] | undefined;
}

export default function MatrixQueryStatus({
  isLoading,
  isError,
  onRetry,
  matrix,
  domains,
  situations,
}: MatrixQueryStatusProps) {
  if (isLoading) return <MatrixSkeleton />;
  if (isError) return <QueryError onRetry={onRetry} />;
  if (!matrix || matrix.total === 0) return <MatrixEmpty />;

  return (
    <MatrixView
      matrix={matrix}
      domains={domains ?? []}
      situations={situations ?? []}
    />
  );
}
