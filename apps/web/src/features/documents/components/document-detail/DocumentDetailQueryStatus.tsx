import { LuFileX } from "react-icons/lu";

import AppCard from "../../../../components/data-display/AppCard";
import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { useLocale } from "../../../../contexts/LocaleContext";
import { isNotFound } from "../../../../services/apiErrors";
import type { DocumentDetail } from "../../types";

import DocumentDetailContent from "./DocumentDetailContent";
import DocumentDetailSkeleton from "./DocumentDetailSkeleton";

export interface DocumentDetailContentData {
  document: DocumentDetail | undefined;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

export interface DocumentDetailQueryStatusProps {
  status: QueryStatus;
  content: DocumentDetailContentData;
}

function DocumentNotFound() {
  const { t } = useLocale();

  return (
    <AppCard>
      <EmptyStateCard
        icon={LuFileX}
        content={{ title: t("documents.not_found") }}
      />
    </AppCard>
  );
}

function renderQueryStatus({
  status,
  content,
}: DocumentDetailQueryStatusProps) {
  const { document, ...titles } = content;

  if (status.isLoading) return <DocumentDetailSkeleton />;
  if (status.isError && !isNotFound(status.error)) {
    return (
      <AppCard>
        <QueryError onRetry={status.onRetry} />
      </AppCard>
    );
  }
  if (!document) return <DocumentNotFound />;

  return <DocumentDetailContent document={document} {...titles} />;
}

export default function DocumentDetailQueryStatus(
  props: DocumentDetailQueryStatusProps,
) {
  return renderQueryStatus(props);
}
