import QueryStatusView from "../../../../components/feedback/QueryStatusView";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { SearchMode } from "../../../candidates/types";
import type { DocumentListResponse } from "../../types";
import DocumentCard from "./DocumentCard";
import DocumentsEmptyState from "./DocumentsEmptyState";
import DocumentsListSkeleton from "./DocumentsListSkeleton";
import SearchModeHint from "./SearchModeHint";

export interface DocumentsListQueryStatusProps {
  status: QueryStatus;
  page: DocumentListResponse | undefined;
  onClearFilters?: () => void;
}

/** "7 documents" when browsing, "7 results" when a search produced the list; both pick the locale's plural form. */
function useCountLabel(mode: SearchMode): (count: number) => string {
  const { t } = useLocale();
  const key = mode === "browse" ? "documents.count" : "documents.result_count";

  return (count) => t(key, { count });
}

function showsCards(
  status: QueryStatus,
  page: DocumentListResponse | undefined,
): boolean {
  return !status.isLoading && !status.isError && (page?.items.length ?? 0) > 0;
}

/** Loading, error, empty and populated states of the documents list; the count is the full result. */
export default function DocumentsListQueryStatus({
  status,
  page,
  onClearFilters,
}: DocumentsListQueryStatusProps) {
  const mode = page?.search_mode ?? "browse";
  const countLabel = useCountLabel(mode);

  return (
    <>
      {showsCards(status, page) ? <SearchModeHint mode={mode} /> : null}
      <QueryStatusView
        status={status}
        items={page?.items}
        slots={{
          getKey: (document) => document.id,
          renderItem: (document) => <DocumentCard document={document} />,
          renderSkeleton: () => <DocumentsListSkeleton />,
          renderEmpty: () => (
            <DocumentsEmptyState onClearFilters={onClearFilters} />
          ),
          countLabel: () => countLabel(page?.total ?? 0),
        }}
      />
    </>
  );
}
