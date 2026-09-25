import { LuFileX } from "react-icons/lu";

import AppCard from "../../../../components/data-display/AppCard";
import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import { useLocale } from "../../../../contexts/LocaleContext";
import { ApiRequestError } from "../../../../services/api";
import type { DocumentDetail } from "../../types";

import DocumentDetailContent from "./DocumentDetailContent";
import DocumentDetailSkeleton from "./DocumentDetailSkeleton";

export interface DocumentDetailQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  document: DocumentDetail | undefined;
  requirementsTitle: string;
  noRequirementsLabel: string;
  officialSourceTitle: string;
}

function DocumentNotFound() {
  const { t } = useLocale();

  return (
    <AppCard>
      <EmptyStateCard icon={LuFileX} title={t("documents.not_found")} />
    </AppCard>
  );
}

function isNotFound(error: unknown) {
  return error instanceof ApiRequestError && error.status === 404;
}

function renderQueryStatus(props: DocumentDetailQueryStatusProps) {
  const { isLoading, isError, error, onRetry, document, ...titles } = props;

  if (isLoading) return <DocumentDetailSkeleton />;
  if (isError && !isNotFound(error)) {
    return (
      <AppCard>
        <QueryError onRetry={onRetry} />
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
