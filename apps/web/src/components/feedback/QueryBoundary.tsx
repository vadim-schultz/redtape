import type { ReactNode } from "react";

import LoadingNote from "./LoadingNote";
import QueryError from "./QueryError";
import type { QueryStatus } from "./queryStatus";

export interface QueryBoundaryProps {
  status: QueryStatus;
  /** Replaces the default `LoadingNote` while the query loads. */
  loading?: ReactNode;
  children: ReactNode;
}

/** Chooses loading, error or content for a query; emptiness stays the caller's call. */
export default function QueryBoundary({
  status,
  loading,
  children,
}: QueryBoundaryProps) {
  if (status.isLoading) return <>{loading ?? <LoadingNote />}</>;
  if (status.isError) return <QueryError onRetry={status.onRetry} />;

  return <>{children}</>;
}
