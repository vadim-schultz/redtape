import { LuFileSearch } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryStatusView from "../../../../components/feedback/QueryStatusView";
import { useLocale } from "../../../../contexts/LocaleContext";

import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";
import DocumentsListSkeleton from "./DocumentsListSkeleton";

export interface DocumentsListQueryStatusProps {
  isLoading: boolean;
  isRefreshing: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  documents: DocumentSummary[] | undefined;
}

function EmptyDocumentsState() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuFileSearch}
      title={t("documents.empty_title")}
      description={t("documents.empty_description")}
    />
  );
}

export default function DocumentsListQueryStatus({
  documents,
  ...status
}: DocumentsListQueryStatusProps) {
  const { t } = useLocale();
  const countKey = (count: number) =>
    count === 1 ? "count_one" : "count_other";

  return (
    <QueryStatusView
      {...status}
      items={documents}
      getKey={(d) => d.id}
      renderItem={(d) => <DocumentCard document={d} />}
      renderSkeleton={() => <DocumentsListSkeleton />}
      renderEmpty={() => <EmptyDocumentsState />}
      countLabel={(count) => t(`documents.${countKey(count)}`, { count })}
    />
  );
}
