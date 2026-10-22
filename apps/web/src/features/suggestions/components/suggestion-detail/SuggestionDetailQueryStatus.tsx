import { LuFileX } from "react-icons/lu";

import AppCard from "../../../../components/data-display/AppCard";
import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import { useLocale } from "../../../../contexts/LocaleContext";
import { ApiRequestError } from "../../../../services/api";
import type { SuggestionRead } from "../../types";

import SuggestionDetailContent from "./SuggestionDetailContent";
import SuggestionDetailSkeleton from "./SuggestionDetailSkeleton";

export interface SuggestionDetailQueryStatusProps {
  status: QueryStatus;
  suggestion: SuggestionRead | undefined;
}

function SuggestionNotFound() {
  const { t } = useLocale();

  return (
    <AppCard>
      <EmptyStateCard
        icon={LuFileX}
        content={{ title: t("suggestions.not_found") }}
      />
    </AppCard>
  );
}

function isNotFound(error: unknown) {
  return error instanceof ApiRequestError && error.status === 404;
}

function renderQueryStatus({
  status,
  suggestion,
}: SuggestionDetailQueryStatusProps) {
  if (status.isLoading) return <SuggestionDetailSkeleton />;
  if (status.isError && !isNotFound(status.error)) {
    return (
      <AppCard>
        <QueryError onRetry={status.onRetry} />
      </AppCard>
    );
  }
  if (!suggestion) return <SuggestionNotFound />;

  return <SuggestionDetailContent suggestion={suggestion} />;
}

export default function SuggestionDetailQueryStatus(
  props: SuggestionDetailQueryStatusProps,
) {
  return renderQueryStatus(props);
}
