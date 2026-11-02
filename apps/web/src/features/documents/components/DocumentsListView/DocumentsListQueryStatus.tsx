import { LuFileSearch } from "react-icons/lu";

import NamespacedEmptyState from "../../../../components/feedback/NamespacedEmptyState";
import QueryStatusView from "../../../../components/feedback/QueryStatusView";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { useCountLabel } from "../../../../components/feedback/useCountLabel";
import type { DocumentListResponse } from "../../types";
import DocumentCard from "./DocumentCard";
import DocumentsListSkeleton from "./DocumentsListSkeleton";

export interface DocumentsListQueryStatusProps {
  status: QueryStatus;
  page: DocumentListResponse | undefined;
}

/** Loading, error, empty and populated states of the documents list; the count is the full result. */
export default function DocumentsListQueryStatus({
  status,
  page,
}: DocumentsListQueryStatusProps) {
  const countLabel = useCountLabel("documents");

  return (
    <QueryStatusView
      status={status}
      items={page?.items}
      slots={{
        getKey: (document) => document.id,
        renderItem: (document) => <DocumentCard document={document} />,
        renderSkeleton: () => <DocumentsListSkeleton />,
        renderEmpty: () => (
          <NamespacedEmptyState namespace="documents" icon={LuFileSearch} />
        ),
        countLabel: () => countLabel(page?.total ?? 0),
      }}
    />
  );
}
