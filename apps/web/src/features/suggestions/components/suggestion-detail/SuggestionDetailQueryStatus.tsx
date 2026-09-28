import { LuFileX } from "react-icons/lu";

import AppCard from "../../../../components/data-display/AppCard";
import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import QueryError from "../../../../components/feedback/QueryError";
import { useLocale } from "../../../../contexts/LocaleContext";
import { ApiRequestError } from "../../../../services/api";
import type { SuggestionRead } from "../../types";

import SuggestionDetailContent from "./SuggestionDetailContent";
import SuggestionDetailSkeleton from "./SuggestionDetailSkeleton";

export interface SuggestionDetailQueryStatusProps {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  suggestion: SuggestionRead | undefined;
}

function SuggestionNotFound() {
  const { t } = useLocale();

  return (
    <AppCard>
      <EmptyStateCard icon={LuFileX} title={t("suggestions.not_found")} />
    </AppCard>
  );
}

function isNotFound(error: unknown) {
  return error instanceof ApiRequestError && error.status === 404;
}

function renderQueryStatus(props: SuggestionDetailQueryStatusProps) {
  const { isLoading, isError, error, onRetry, suggestion } = props;

  if (isLoading) return <SuggestionDetailSkeleton />;
  if (isError && !isNotFound(error)) {
    return (
      <AppCard>
        <QueryError onRetry={onRetry} />
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
