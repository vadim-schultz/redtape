import { LuInbox } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import QueryStatusView from "../../../../components/feedback/QueryStatusView";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { SuggestionRead } from "../../types";

import SuggestionCard from "./SuggestionCard";
import SuggestionsListSkeleton from "./SuggestionsListSkeleton";

export interface SuggestionsListQueryStatusProps {
  status: QueryStatus;
  suggestions: SuggestionRead[] | undefined;
}

function EmptySuggestionsState() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuInbox}
      content={{
        title: t("suggestions.empty_title"),
        description: t("suggestions.empty_description"),
      }}
    />
  );
}

export default function SuggestionsListQueryStatus({
  suggestions,
  status,
}: SuggestionsListQueryStatusProps) {
  const { t } = useLocale();
  const countKey = (count: number) =>
    count === 1 ? "count_one" : "count_other";

  return (
    <QueryStatusView
      status={status}
      items={suggestions}
      slots={{
        getKey: (s) => s.id,
        renderItem: (s) => <SuggestionCard suggestion={s} />,
        renderSkeleton: () => <SuggestionsListSkeleton />,
        renderEmpty: () => <EmptySuggestionsState />,
        countLabel: (count) => t(`suggestions.${countKey(count)}`, { count }),
      }}
    />
  );
}
